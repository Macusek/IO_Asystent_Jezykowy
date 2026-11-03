import argparse
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from . import auth
from .db import initialize

ROOT = Path(__file__).resolve().parent.parent

def create_app(db_path=None, llm=None, dev=False, smtp=None, public_url='http://127.0.0.1:8000', secure_cookie=False):
    @asynccontextmanager
    async def lifespan(app):
        if app.state.llm is None:
            from .llm import GroqClient, read_key
            app.state.llm = GroqClient(read_key(ROOT / 'groq_api_key.txt'))
        initialize(app.state.db_path)
        yield
        close = getattr(app.state.llm, 'close', None)
        if close:
            close()

    app = FastAPI(title='LanguageMate', lifespan=lifespan)
    app.state.db_path = db_path or ROOT / 'data/app.sqlite3'
    app.state.llm = llm
    app.state.dev = dev
    app.state.smtp = smtp
    app.state.public_url = public_url.rstrip('/')
    app.state.secure_cookie = secure_cookie

    @app.middleware('http')
    async def security(request: Request, call_next):
        if request.method in ('POST','PUT','DELETE','PATCH'):
            origin = request.headers.get('origin')
            expected = urlsplit(str(request.base_url))
            if (origin and origin != f'{expected.scheme}://{expected.netloc}') or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail':'Żądanie z obcej strony zostało odrzucone.'}, status_code=403)
            if request.headers.get('content-type','').split(';')[0] != 'application/json':
                return JSONResponse({'detail':'Wymagany format JSON.'}, status_code=415)
            if int(request.headers.get('content-length','0') or '0') > 65536:
                return JSONResponse({'detail':'Żądanie jest za duże.'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({'detail':'Nieprawidłowe dane. Sprawdź e-mail, hasło (10–128 znaków) i pozostałe pola.'}, status_code=422)

    app.include_router(auth.router)
    from .conversations import router as conversations_router
    app.include_router(conversations_router)
    from .stats import router as stats_router
    app.include_router(stats_router)
    from .web import router as web_router
    app.include_router(web_router)
    return app

def main():
    parser = argparse.ArgumentParser(description='LanguageMate — nauka języków z AI')
    parser.add_argument('--dev', action='store_true', help='Jawny tryb deweloperski: link resetu hasła w terminalu bez SMTP.')
    parser.add_argument('--smtp-config', type=Path)
    parser.add_argument('--public-url', default='http://127.0.0.1:8000')
    parser.add_argument('--secure-cookie', action='store_true')
    args = parser.parse_args()
    from .llm import read_key
    try:
        read_key(ROOT / 'groq_api_key.txt')
    except RuntimeError as error:
        parser.exit(1, str(error)+'\n')
    smtp = json.loads(args.smtp_config.read_text('utf-8')) if args.smtp_config else None
    import uvicorn
    uvicorn.run(create_app(dev=args.dev, smtp=smtp, public_url=args.public_url, secure_cookie=args.secure_cookie), host='127.0.0.1', port=8000, access_log=False)

if __name__ == '__main__':
    main()
