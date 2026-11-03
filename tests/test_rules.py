import httpx
import pytest
from app.text import sentences,words
from app.llm import GroqClient,LLMError
from app.main import create_app
from fastapi.testclient import TestClient
from test_auth import client,account
from test_stats import conversation
from stubs import StubLLM
from app.db import connect

@pytest.mark.parametrize('text,expected',[
    ('Hello! How are you? Fine.', ['Hello!','How are you?','Fine.']),
    ('Pierwsza linia\nDruga linia', ['Pierwsza linia','Druga linia']),
    ('... ! ? 123', []),
    ('¡Hola! ¿Cómo estás?', ['¡Hola!','¿Cómo estás?']),
    (' Dr. Smith ma 2.5 kota. ', ['Dr.','Smith ma 2.','5 kota.']),
    ('Bez kropki', ['Bez kropki'])])
def test_sentence_rules(text,expected):
    assert sentences(text)==expected

def test_word_rules():
    tokens=words("Żółć ŻÓŁĆ man\u0303ana mañana don't l’été e-mail 123 _ 🚀")
    assert tokens==['żółć','żółć','mañana','mañana',"don't","l'été",'e-mail']
    assert len(set(tokens))==5

def test_retry_after():
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(429,headers={'Retry-After':'0'})
    c=GroqClient('dummy-test-value',transport=httpx.MockTransport(handler),sleep=lambda _:None)
    with pytest.raises(LLMError):c.complete([],'ES','C1','Hola.')
    assert len(calls)==2
    c.close()

@pytest.mark.parametrize('data',[
    {'choices':[]},
    {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
    {'choices':[{'finish_reason':'stop','message':{'content':None}}]},
    {'choices':[{'finish_reason':'stop','message':{'content':'not JSON'}}]}])
def test_malformed_provider(data):
    c=GroqClient('dummy-test-value',transport=httpx.MockTransport(lambda _:httpx.Response(200,json=data)))
    with pytest.raises(LLMError):c.complete([],'PL','A1','Cześć.')
    c.close()

def test_invalid_model_response_has_no_partial_assessment(client):
    account(client)
    client.app.state.llm=StubLLM({'reply':'ok','errors':[{'sentence_index':2,'zdanie':'Hi.','korekta':'Hello.','opis':'Opis.'}]})
    cid=client.post('/api/conversations',json={'language':'EN','level':'C1'}).json()['id']
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hi.'}).status_code==502
    client.post(f'/api/conversations/{cid}/finish',json={})
    summary=client.get(f'/api/conversations/{cid}/summary').json()
    assert summary['errors']==[] and summary['stats']['assessed_sentences']==0
    assert summary['stats']['unassessed_sentences']==1

def test_active_not_counted_and_reset_does_not_recount(client):
    account(client)
    cid=conversation(client)
    active=client.post('/api/conversations',json={'language':'EN','level':'A1'}).json()['id']
    client.post(f'/api/conversations/{active}/messages',json={'text':'New words.'})
    assert client.get('/api/stats/EN').json()['words_spoken']==3
    client.post('/api/stats/EN/reset',json={})
    client.post(f'/api/conversations/{cid}/finish',json={})
    assert client.get('/api/stats/EN').json()['words_spoken']==0
    client.post(f'/api/conversations/{active}/finish',json={})
    assert client.get('/api/stats/EN').json()['words_spoken']==2

def test_ui_and_session_cookie(client):
    account(client)
    assert 'HttpOnly' in client.post('/api/auth/login',json={'email':'ewa@example.com','password':'bezpieczne-haslo123'}).headers['set-cookie']
    r=client.get('/')
    assert r.status_code==200 and '<html lang="pl">' in r.text
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/assets/style.css').status_code==200
    assert client.get('/assets/groq_api_key.txt').status_code==404
    assert client.get('/api/stats/DE').status_code==422

def test_server_restart_persists_data(client):
    body=account(client)
    cid=conversation(client)
    with TestClient(create_app(client.app.state.db_path,llm=StubLLM())) as other:
        assert other.post('/api/auth/login',json=body).status_code==200
        assert other.get(f'/api/conversations/{cid}/summary').json()['stats']['words_spoken']==3
        assert other.get('/api/stats/EN').json()['words_spoken']==3

def test_parallel_turn_rejected(client):
    from app.conversations import conversation_lock
    account(client)
    cid=client.post('/api/conversations',json={'language':'PL','level':'A1'}).json()['id']
    with conversation_lock(cid):
        assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Cześć.'}).status_code==409
        assert client.post(f'/api/conversations/{cid}/finish',json={}).status_code==409

def test_repeated_sentences_are_separate(client):
    account(client)
    client.app.state.llm=StubLLM({'reply':'Hello!','errors':[
        {'sentence_index':0,'zdanie':'I is happy.','korekta':'I am happy.','opis':'Odmiana.'},
        {'sentence_index':1,'zdanie':'I is happy.','korekta':'I am happy.','opis':'Odmiana.'}]})
    conversation(client,text='I is happy. I is happy.')
    report=client.get('/api/stats/EN').json()
    assert report['incorrect_sentences']==2 and report['error_percent']==100

def test_weighted_tempo_and_unique_union(client):
    account(client)
    conversation(client,text='Hello hello.',seconds=60)
    conversation(client,text='Hello world again.',seconds=180)
    report=client.get('/api/stats/EN').json()
    assert report['words_spoken']==5 and report['unique_words']==3
    assert report['words_per_minute']==1.25

def test_normal_start_requires_file_even_with_environment_key(tmp_path,monkeypatch):
    monkeypatch.setattr('app.main.ROOT',tmp_path)
    monkeypatch.setenv('GROQ_API_KEY','dummy-environment-value')
    with pytest.raises(RuntimeError,match='Brak pliku groq_api_key.txt'):
        with TestClient(create_app(tmp_path/'never.sqlite3')):
            pass
    assert not (tmp_path/'never.sqlite3').exists()
