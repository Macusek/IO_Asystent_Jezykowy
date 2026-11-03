import logging
import re
import time
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.db import connect

@pytest.fixture
def client(tmp_path):
    from stubs import StubLLM
    with TestClient(create_app(tmp_path/'test.sqlite3', llm=StubLLM(), dev=True)) as c:
        yield c

def account(client, email='ewa@example.com'):
    body = {'email':email, 'password':'bezpieczne-haslo123'}
    assert client.post('/api/auth/register',json=body).status_code == 200
    assert client.post('/api/auth/login',json=body).status_code == 200
    return body

def test_auth(client):
    body=account(client)
    assert client.get('/api/auth/me').json()['email']==body['email']
    assert client.post('/api/auth/register',json={**body,'email':'EWA@example.com'}).status_code==409
    with connect(client.app.state.db_path) as db:
        value=db.execute('SELECT password_hash FROM users').fetchone()[0]
        assert value.startswith('$argon2id$') and body['password'] not in value
    assert client.post('/api/auth/login',json={**body,'password':'niepoprawne-haslo'}).status_code==401
    client.post('/api/auth/logout',json={})
    assert client.get('/api/auth/me').status_code==401

def test_reset(client,caplog):
    body=account(client)
    with caplog.at_level(logging.WARNING):
        assert client.post('/api/auth/forgot',json={'email':body['email']}).status_code==200
    token=re.search(r'reset=([\w-]+)',caplog.text).group(1)
    with connect(client.app.state.db_path) as db:
        assert db.execute('SELECT token FROM reset_tokens').fetchone()[0]!=token
    payload={'token':token,'password':'nowe-bezpieczne123'}
    assert client.post('/api/auth/reset',json=payload).status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/reset',json=payload).status_code==400
    assert client.post('/api/auth/login',json={**body,'password':payload['password']}).status_code==200

def test_expired_and_production_reset(client,caplog):
    body=account(client)
    with caplog.at_level(logging.WARNING):
        client.post('/api/auth/forgot',json={'email':body['email']})
    token=re.search(r'reset=([\w-]+)',caplog.text).group(1)
    with connect(client.app.state.db_path) as db:
        db.execute('UPDATE reset_tokens SET expires=?',(time.time()-1,))
    assert client.post('/api/auth/reset',json={'token':token,'password':'kolejne-haslo123'}).status_code==400
    client.app.state.dev=False
    caplog.clear()
    assert client.post('/api/auth/forgot',json={'email':body['email']}).status_code==503
    assert not caplog.text

def test_csrf(client):
    assert client.post('/api/auth/logout',json={},headers={'origin':'https://obca.example'}).status_code==403

def test_smtp_reset(client,monkeypatch,caplog):
    body=account(client)
    sent=[]
    class SMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def starttls(self):sent.append('tls')
        def login(self,*args):sent.append('login')
        def send_message(self,msg):sent.append(msg)
    monkeypatch.setattr('app.auth.smtplib.SMTP',SMTP)
    client.app.state.dev=False
    client.app.state.smtp={'host':'smtp.example.com','sender':'noreply@example.com','username':'x','password':'local-test-only'}
    caplog.clear()
    assert client.post('/api/auth/forgot',json={'email':body['email']}).status_code==200
    assert sent[:2]==['tls','login']
    token=re.search(r'reset=([\w-]+)',sent[2].get_content()).group(1)
    assert token not in caplog.text
    assert client.post('/api/auth/reset',json={'token':token,'password':'nowe-smtp-haslo123'}).status_code==200
