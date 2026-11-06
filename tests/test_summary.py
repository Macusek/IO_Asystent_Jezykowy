from test_auth import client,account
from stubs import StubLLM
from app.db import connect

def test_summary(client):
    account(client)
    client.app.state.llm=StubLLM({'reply':'¿Qué te gusta?','errors':[
        {'sentence_index':0,'zdanie':'Yo tiene años.','korekta':'Yo tengo veinte años.','opis':'Odmiana czasownika.'},
        {'sentence_index':0,'zdanie':'Yo tiene años.','korekta':'Yo tengo veinte años.','opis':'Brak liczby lat.'}]})
    cid=client.post('/api/conversations',json={'language':'ES','level':'A1'}).json()['id']
    assert client.get(f'/api/conversations/{cid}/summary').status_code==409
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Yo tiene años.'}).status_code==200
    live=client.get(f'/api/conversations/{cid}').json()
    assert live['end_ts'] is None and len(live['errors'])==2
    assert live['errors'][0]['correction']=='Yo tengo veinte años.'
    summary=client.post(f'/api/conversations/{cid}/finish',json={}).json()
    assert len(summary['errors'])==2 and summary['errors'][0]['description']=='Odmiana czasownika.'
    assert summary==client.post(f'/api/conversations/{cid}/finish',json={}).json()
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hola.'}).status_code==409
    assert [m['text'] for m in summary['messages']]==['Yo tiene años.','¿Qué te gusta?']
    history=client.get('/api/conversations/history').json()
    assert [c['id'] for c in history]==[cid] and history[0]['user_messages']==1 and history[0]['error_count']==2
    account(client,'obca@example.com')
    assert client.get(f'/api/conversations/{cid}/summary').status_code==404
    assert client.post(f'/api/conversations/{cid}/finish',json={}).status_code==404
    assert client.post(f'/api/conversations/{cid}/resume',json={}).status_code==404
    assert client.get('/api/conversations/history').json()==[]

def test_resume(client):
    account(client)
    client.app.state.llm=StubLLM()
    cid=client.post('/api/conversations',json={'language':'ES','level':'A1'}).json()['id']
    with connect(client.app.state.db_path) as db:
        db.execute('UPDATE conversations SET start_ts=?,end_ts=? WHERE id=?',(1000.0,1600.0,cid))
    assert client.post(f'/api/conversations/{cid}/resume',json={}).status_code==200
    assert client.get('/api/conversations/history').json()==[]
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hola.'}).status_code==200
    summary=client.post(f'/api/conversations/{cid}/finish',json={}).json()
    assert 600<=summary['stats']['duration_seconds']<660
