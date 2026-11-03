from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router=APIRouter()
STATIC=Path(__file__).parent/'static'

@router.get('/')
def home():
    return FileResponse(STATIC/'index.html')

@router.get('/assets/{name}')
def asset(name: str):
    if name not in ('app.js','style.css'):
        from fastapi import HTTPException
        raise HTTPException(404,'Nie znaleziono pliku.')
    return FileResponse(STATIC/name)
