import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, level TEXT DEFAULT 'A1');
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS reset_tokens(token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL NOT NULL, used INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), language TEXT CHECK(language IN ('PL','EN','ES')), level TEXT CHECK(level IN ('A1','A2','B1','B2','C1','C2')), start_ts REAL NOT NULL, end_ts REAL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL REFERENCES conversations(id), author TEXT CHECK(author IN ('user','ai')), text TEXT NOT NULL, timestamp REAL NOT NULL, status TEXT DEFAULT 'pending', sentence_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS errors(id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES messages(id), sentence_index INTEGER NOT NULL, sentence TEXT NOT NULL, correction TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stats_resets(user_id INTEGER REFERENCES users(id), language TEXT, reset_ts REAL NOT NULL DEFAULT 0, PRIMARY KEY(user_id,language));
CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS conversations_user ON conversations(user_id);
'''

@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript(SCHEMA)
        if 'reset_ts' not in [row['name'] for row in db.execute('PRAGMA table_info(stats_resets)')]:
            db.execute('ALTER TABLE stats_resets RENAME COLUMN through_id TO reset_ts')

if __name__ == '__main__':
    initialize(Path(__file__).resolve().parent.parent / 'data/app.sqlite3')
    print('Baza danych gotowa.')
