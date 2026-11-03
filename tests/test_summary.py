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
    account(client,'obca@example.com')
    assert client.get(f'/api/conversations/{cid}/summary').status_code==404
    assert client.post(f'/api/conversations/{cid}/finish',json={}).status_code==404
