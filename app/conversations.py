import threading
import time
from contextlib import contextmanager
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from .auth import current_user
from .db import connect
from .text import sentences

router=APIRouter(prefix='/api/conversations')
Language=Literal['PL','EN','ES']
Level=Literal['A1','A2','B1','B2','C1','C2']

class ConversationInput(BaseModel):
    language: Language
    level: Level

class MessageInput(BaseModel):
    text: str=Field(min_length=1,max_length=4000)

    @field_validator('text')
    @classmethod
    def meaningful(cls,value):
        value=value.strip()
        if not value or not sentences(value):
            raise ValueError('Wpisz przynajmniej jedno słowo.')
        return value

def owned(db,conversation_id,user_id):
    row=db.execute('SELECT * FROM conversations WHERE id=? AND user_id=?',(conversation_id,user_id)).fetchone()
    if not row:
        raise HTTPException(404,'Nie znaleziono rozmowy.')
    return dict(row)

# Stała liczba blokad nie rośnie wraz z liczbą rozmów. Operacje jednej rozmowy są serializowane.
LOCKS=[threading.Lock() for _ in range(128)]

@contextmanager
def conversation_lock(cid):
    lock=LOCKS[cid % len(LOCKS)]
    if not lock.acquire(blocking=False):
        raise HTTPException(409,'Trwa przetwarzanie tej rozmowy. Poczekaj na zakończenie tury.')
    try:
        yield
    finally:
        lock.release()

@router.post('')
def start(body: ConversationInput,request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        cid=db.execute('INSERT INTO conversations(user_id,language,level,start_ts) VALUES (?,?,?,?)',(user['id'],body.language,body.level,time.time())).lastrowid
        db.execute('UPDATE users SET level=? WHERE id=?',(body.level,user['id']))
    return {'id':cid,'language':body.language,'level':body.level}

@router.get('')
def active(request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        return [dict(r) for r in db.execute('SELECT * FROM conversations WHERE user_id=? AND end_ts IS NULL ORDER BY id DESC',(user['id'],))]

@router.get('/{cid}')
def detail(cid: int,request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        conversation=owned(db,cid,user['id'])
        conversation['messages']=[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY id',(cid,))]
        conversation['errors']=[dict(r) for r in db.execute('SELECT e.* FROM errors e JOIN messages m ON m.id=e.message_id WHERE m.conversation_id=? ORDER BY m.id,e.sentence_index,e.id',(cid,))]
    return conversation

@router.post('/{cid}/finish')
def finish(cid: int,request: Request):
    user=current_user(request)
    with conversation_lock(cid):
        with connect(request.app.state.db_path) as db:
            conversation=owned(db,cid,user['id'])
            if conversation['end_ts'] is None:
                db.execute('UPDATE conversations SET end_ts=? WHERE id=?',(max(time.time(),conversation['start_ts']),cid))
    return summary(cid,request)

@router.get('/{cid}/summary')
def summary(cid: int,request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        conversation=owned(db,cid,user['id'])
        if conversation['end_ts'] is None:
            raise HTTPException(409,'Najpierw zakończ rozmowę.')
        errors=[dict(r) for r in db.execute('SELECT e.* FROM errors e JOIN messages m ON m.id=e.message_id WHERE m.conversation_id=? ORDER BY m.id,e.sentence_index,e.id',(cid,))]
        unassessed=db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND author='user' AND status!='evaluated'",(cid,)).fetchone()[0]
        from .stats import conversation_stats
        stats=conversation_stats(db,cid)
    return {'conversation':conversation,'errors':errors,'unassessed_messages':unassessed,'stats':stats}

@router.post('/{cid}/messages')
def send(cid: int,body: MessageInput,request: Request):
    user=current_user(request)
    with conversation_lock(cid):
        with connect(request.app.state.db_path) as db:
            conversation=owned(db,cid,user['id'])
            if conversation['end_ts'] is not None:
                raise HTTPException(409,'Ta rozmowa została już zakończona.')
            mid=db.execute('INSERT INTO messages(conversation_id,author,text,timestamp,sentence_count) VALUES (?,?,?,?,?)',(cid,'user',body.text,time.time(),len(sentences(body.text)))).lastrowid
        from .llm import LLMError, validate_result
        with connect(request.app.state.db_path) as db:
            history=[{'role':'assistant' if r['author']=='ai' else 'user','content':r['text']} for r in db.execute('SELECT author,text FROM messages WHERE conversation_id=? ORDER BY id',(cid,))]
        try:
            result=request.app.state.llm.complete(history,conversation['language'],conversation['level'],body.text)
            # Ta sama walidacja także dla wstrzykniętych klientów; brak częściowych ocen.
            result=validate_result(result.model_dump() if hasattr(result,'model_dump') else result,body.text)
        except LLMError as error:
            with connect(request.app.state.db_path) as db:
                db.execute("UPDATE messages SET status='failed' WHERE id=?",(mid,))
            raise HTTPException(502,str(error)) from None
        with connect(request.app.state.db_path) as db:
            db.execute("UPDATE messages SET status='evaluated' WHERE id=?",(mid,))
            db.execute('INSERT INTO messages(conversation_id,author,text,timestamp,status) VALUES (?,?,?,?,?)',(cid,'ai',result.reply,time.time(),'complete'))
            db.executemany('INSERT INTO errors(message_id,sentence_index,sentence,correction,description) VALUES (?,?,?,?,?)',[(mid,e.sentence_index,e.zdanie,e.korekta,e.opis) for e in result.errors])
        return {'message_id':mid,'status':'evaluated'}
