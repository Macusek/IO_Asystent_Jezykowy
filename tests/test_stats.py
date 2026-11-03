import pytest
from test_auth import client,account
from app.db import connect
from stubs import StubLLM

def conversation(client,language='EN',text='Hello hello. Bye!',seconds=120):
    cid=client.post('/api/conversations',json={'language':language,'level':'B1'}).json()['id']
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':text}).status_code==200
    client.post(f'/api/conversations/{cid}/finish',json={})
    with connect(client.app.state.db_path) as db:
        db.execute('UPDATE conversations SET start_ts=end_ts-? WHERE id=?',(seconds,cid))
    return cid

def test_statistics(client):
    account(client)
    client.app.state.llm=StubLLM({'reply':'Hi!','errors':[
        {'sentence_index':0,'zdanie':'Hello hello.','korekta':'Hello.','opis':'Powtórzenie.'},
        {'sentence_index':0,'zdanie':'Hello hello.','korekta':'Hello.','opis':'Druga uwaga.'}]})
    cid=conversation(client)
    report=client.get('/api/stats/EN').json()
    assert report['incorrect_sentences']==1 and report['correct_sentences']==1
    assert report['error_percent']==50
    assert report['words_per_minute']==1.5
    assert report['words_spoken']==3 and report['unique_words']==2
    client.post(f'/api/conversations/{cid}/finish',json={})
    assert report==client.get('/api/stats/EN').json()
    conversation(client)
    report=client.get('/api/stats/EN').json()
    assert report['words_spoken']==6 and report['unique_words']==2 and report['words_per_minute']==1.5

def test_reset_isolation(client):
    account(client)
    conversation(client)
    conversation(client,'ES')
    client.post('/api/stats/EN/reset',json={})
    assert client.get('/api/stats/EN').json()['words_spoken']==0
    assert client.get('/api/stats/ES').json()['words_spoken']==3
    conversation(client)
    assert client.get('/api/stats/EN').json()['words_spoken']==3
    account(client,'druga@example.com')
    assert client.get('/api/stats/ES').json()['words_spoken']==0
    conversation(client,'ES')
    client.post('/api/stats/ES/reset',json={})
    client.post('/api/auth/login',json={'email':'ewa@example.com','password':'bezpieczne-haslo123'})
    assert client.get('/api/stats/ES').json()['words_spoken']==3

def test_zero_time_and_no_assessment(client):
    account(client)
    assert client.get('/api/stats/PL').json()['error_percent']==0
    client.app.state.llm=StubLLM(error='Test awarii')
    cid=client.post('/api/conversations',json={'language':'PL','level':'C2'}).json()['id']
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Ala ma kota.'}).status_code==502
    client.post(f'/api/conversations/{cid}/finish',json={})
    with connect(client.app.state.db_path) as db:
        db.execute('UPDATE conversations SET start_ts=end_ts WHERE id=?',(cid,))
    report=client.get('/api/stats/PL').json()
    assert report['words_per_minute']==0 and report['error_percent']==0
    assert report['correct_sentences']==report['incorrect_sentences']==0
    assert report['unassessed_sentences']==1 and report['words_spoken']==3
