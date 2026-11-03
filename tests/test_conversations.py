from test_auth import client, account

def test_conversations(client):
    account(client)
    for language in ('PL','EN','ES'):
        for level in ('A1','A2','B1','B2','C1','C2'):
            response=client.post('/api/conversations',json={'language':language,'level':level})
            assert response.status_code==200
    cid=response.json()['id']
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hola.'}).status_code==200
    assert client.get(f'/api/conversations/{cid}').json()['messages'][0]['text']=='Hola.'
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'   '}).status_code==422
    assert client.post('/api/conversations',json={'language':'DE','level':'A0'}).status_code==422
    account(client,'inna@example.com')
    assert client.get(f'/api/conversations/{cid}').status_code==404
    assert client.post(f'/api/conversations/{cid}/messages',json={'text':'Hello.'}).status_code==404
