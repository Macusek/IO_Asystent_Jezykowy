import time
from fastapi import APIRouter,Request
from .auth import current_user
from .conversations import Language
from .db import connect
from .text import words

router=APIRouter(prefix='/api/stats')

def calculate(db,conversations):
    correct=incorrect=word_count=unassessed=0
    unique=set()
    duration=0.0
    for c in conversations:
        duration+=max(0,c['end_ts']-c['start_ts'])
        for m in db.execute("SELECT * FROM messages WHERE conversation_id=? AND author='user'",(c['id'],)):
            tokens=words(m['text'])
            word_count+=len(tokens)
            unique.update(tokens)
            if m['status']=='evaluated':
                bad=db.execute('SELECT COUNT(DISTINCT sentence_index) FROM errors WHERE message_id=?',(m['id'],)).fetchone()[0]
                incorrect+=bad
                correct+=max(0,m['sentence_count']-bad)
            else:
                unassessed+=m['sentence_count']
    assessed=correct+incorrect
    return {'correct_sentences':correct,'incorrect_sentences':incorrect,
            'error_percent':incorrect/assessed*100 if assessed else 0.0,
            'words_per_minute':word_count/(duration/60) if duration>0 else 0.0,
            'words_spoken':word_count,'unique_words':len(unique),'duration_seconds':duration,
            'assessed_sentences':assessed,'unassessed_sentences':unassessed}

def conversation_stats(db,cid):
    return calculate(db,db.execute('SELECT * FROM conversations WHERE id=? AND end_ts IS NOT NULL',(cid,)).fetchall())

@router.get('/{language}')
def report(language: Language,request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        reset=db.execute('SELECT reset_ts FROM stats_resets WHERE user_id=? AND language=?',(user['id'],language)).fetchone()
        boundary=reset[0] if reset else None
        conversations=db.execute('SELECT * FROM conversations WHERE user_id=? AND language=? AND end_ts IS NOT NULL AND (? IS NULL OR end_ts>?)',(user['id'],language,boundary,boundary)).fetchall()
        return {'language':language,**calculate(db,conversations)}

@router.post('/{language}/reset')
def reset(language: Language,request: Request):
    user=current_user(request)
    with connect(request.app.state.db_path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO stats_resets(user_id,language,reset_ts) VALUES (?,?,?) ON CONFLICT(user_id,language) DO UPDATE SET reset_ts=excluded.reset_ts',(user['id'],language,time.time()))
    return {'message':'Statystyki dla wybranego języka zostały zresetowane.'}
