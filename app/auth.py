import hashlib
import logging
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from .db import connect

router = APIRouter(prefix='/api/auth')
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class EmailInput(BaseModel):
    email: EmailStr

class ResetInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=10, max_length=128)

def current_user(request: Request):
    with connect(request.app.state.db_path) as db:
        row = db.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=? AND s.expires>?',
                         (digest(request.cookies.get('session', '')), time.time())).fetchone()
    if not row:
        raise HTTPException(401, 'Zaloguj się, aby kontynuować.')
    return dict(row)

@router.post('/register')
def register(body: Credentials, request: Request):
    try:
        with connect(request.app.state.db_path) as db:
            db.execute('INSERT INTO users(email,password_hash) VALUES (?,?)', (str(body.email).casefold(), hasher.hash(body.password)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Konto z tym adresem już istnieje.')
    return {'message': 'Konto utworzone. Zaloguj się.'}

@router.post('/login')
def login(body: Credentials, request: Request, response: Response):
    with connect(request.app.state.db_path) as db:
        user = db.execute('SELECT * FROM users WHERE email=?', (str(body.email).casefold(),)).fetchone()
        try:
            hasher.verify(user['password_hash'] if user else DUMMY_HASH, body.password)
        except (VerificationError, InvalidHashError):
            raise HTTPException(401, 'Nieprawidłowy e-mail lub hasło.')
        if not user:
            raise HTTPException(401, 'Nieprawidłowy e-mail lub hasło.')
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)', (digest(token), user['id'], time.time()+86400))
    response.set_cookie('session', token, httponly=True, samesite='strict', secure=request.app.state.secure_cookie, max_age=86400)
    return {'message': 'Zalogowano.'}

@router.get('/me')
def me(request: Request):
    user = current_user(request)
    return {'email': user['email'], 'level': user['level']}

@router.post('/logout')
def logout(request: Request, response: Response):
    with connect(request.app.state.db_path) as db:
        db.execute('DELETE FROM sessions WHERE token=?', (digest(request.cookies.get('session','')),))
    response.delete_cookie('session')
    return {'message': 'Wylogowano.'}

@router.post('/forgot')
def forgot(body: EmailInput, request: Request):
    state = request.app.state
    if not state.smtp and not state.dev:
        raise HTTPException(503, 'Reset hasła wymaga konfiguracji SMTP lub jawnego trybu deweloperskiego.')
    with connect(state.db_path) as db:
        user = db.execute('SELECT id FROM users WHERE email=?', (str(body.email).casefold(),)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            db.execute('UPDATE reset_tokens SET used=1 WHERE user_id=?', (user['id'],))
            db.execute('INSERT INTO reset_tokens(token,user_id,expires) VALUES (?,?,?)', (digest(token), user['id'], time.time()+1800))
    if user:
        link = state.public_url + '/?reset=' + token
        if state.smtp:
            msg = EmailMessage()
            msg['Subject'] = 'LanguageMate — reset hasła'
            msg['From'] = state.smtp['sender']
            msg['To'] = str(body.email)
            msg.set_content('Ustaw nowe hasło (link ważny 30 minut):\n'+link)
            try:
                with smtplib.SMTP(state.smtp['host'], state.smtp.get('port',587), timeout=15) as server:
                    server.starttls()
                    if state.smtp.get('username'):
                        server.login(state.smtp['username'], state.smtp['password'])
                    server.send_message(msg)
            except (OSError, smtplib.SMTPException):
                raise HTTPException(503, 'Nie udało się wysłać wiadomości resetującej.')
        else:
            logging.getLogger('uvicorn.error').warning('TRYB DEWELOPERSKI — link resetu: %s', link)
    return {'message': 'Jeśli konto istnieje, wysłano instrukcję. W trybie deweloperskim bez SMTP sprawdź terminal serwera.'}

@router.post('/reset')
def reset(body: ResetInput, request: Request):
    password_hash = hasher.hash(body.password)
    with connect(request.app.state.db_path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM reset_tokens WHERE token=? AND used=0 AND expires>?', (digest(body.token),time.time())).fetchone()
        if not row:
            raise HTTPException(400, 'Link resetu jest nieprawidłowy, wykorzystany lub wygasł.')
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash,row['user_id']))
        db.execute('UPDATE reset_tokens SET used=1 WHERE user_id=?', (row['user_id'],))
        db.execute('DELETE FROM sessions WHERE user_id=?', (row['user_id'],))
    return {'message': 'Hasło zmienione. Zaloguj się ponownie.'}
