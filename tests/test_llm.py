import json
import httpx
import pytest
from app.llm import BASE_URL, MODEL, GroqClient, LLMError, read_key, validate_result
from test_auth import client,account
from stubs import StubLLM

def test_key(tmp_path):
    p=tmp_path/'key'
    with pytest.raises(RuntimeError,match='Brak pliku'):read_key(p)
    p.write_text('\n  \n',encoding='utf-8')
    with pytest.raises(RuntimeError,match='pusty'):read_key(p)
    p.write_text('\n dummy-test-value\nunused',encoding='utf-8')
    assert read_key(p)=='dummy-test-value'
    p.write_text('"dummy-test-value"',encoding='utf-8')
    with pytest.raises(RuntimeError):read_key(p)

@pytest.mark.parametrize('raw',[
    'not json', {'reply':'ok'}, {'reply':' ','errors':[]},
    {'reply':'ok','errors':[{'sentence_index':0,'zdanie':'obce zdanie','korekta':'ok','opis':'opis'}]},
    {'reply':'ok','errors':[{'sentence_index':True,'zdanie':'Hola.','korekta':'ok','opis':'opis'}]},
    {'reply':'ok','errors':[],'extra':1}])
def test_invalid_contract(raw):
    with pytest.raises(LLMError):validate_result(raw,'Hola.')

def test_groq_request():
    def handler(request):
        assert str(request.url)==BASE_URL+'/chat/completions'
        data=json.loads(request.content)
        assert data['model']==MODEL
        assert data['messages'][-1]=={'role':'user','content':'Hola.'}
        assert 'A2' in data['messages'][0]['content'] and 'Spanish' in data['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'reply':'¡Hola!','errors':[]})}}]})
    c=GroqClient('dummy-test-value',transport=httpx.MockTransport(handler))
    assert c.complete([{'role':'user','content':'Hola.'}],'ES','A2','Hola.').reply=='¡Hola!'
    c.close()

@pytest.mark.parametrize('status,attempts,fragment',[(401,1,'klucz'),(403,1,'klucz'),(429,1,'Limit'),(500,2,'Groq'),(400,1,'Groq')])
def test_http_errors(status,attempts,fragment):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status,json={'error':'never expose raw errors'})
    c=GroqClient('dummy-test-value',transport=httpx.MockTransport(handler),sleep=lambda _:None)
    with pytest.raises(LLMError,match=fragment):c.complete([],'EN','B1','Hi.')
    assert len(calls)==attempts
    c.close()

@pytest.mark.parametrize('kind,attempts',[(httpx.ConnectError,2),(httpx.ReadTimeout,1)])
def test_network_errors(kind,attempts):
    calls=[]
    def handler(request):
        calls.append(request)
        raise kind('private detail',request=request)
    c=GroqClient('dummy-test-value',transport=httpx.MockTransport(handler),sleep=lambda _:None)
    with pytest.raises(LLMError):c.complete([],'PL','C2','Cześć.')
    assert len(calls)==attempts
    c.close()

def test_failure_preserves_message(client):
    account(client)
    cid=client.post('/api/conversations',json={'language':'EN','level':'B1'}).json()['id']
    client.app.state.llm=StubLLM(error='Brak połączenia. Zapisano bez oceny.')
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hello world.'}).status_code==502
    messages=client.get(f'/api/conversations/{cid}').json()['messages']
    assert len(messages)==1 and messages[0]['status']=='failed'
    client.app.state.llm=StubLLM()
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hello again.'}).status_code==200
    assert client.app.state.llm.calls[0][0][0]['content']=='Hello world.'
