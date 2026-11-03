"""Serwer wyłącznie do testów przeglądarkowych: izolowana baza i jawny stub."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import uvicorn
from app.main import create_app
from app.llm import LLMError
from app.text import sentences

class BrowserStub:
    def complete(self,history,language,level,text):
        if text=='AWARIA':
            raise LLMError('Test awarii Groq. Wiadomość zapisana bez oceny.')
        errors=[]
        for i,s in enumerate(sentences(text)):
            if 'Yo tiene' in s:
                errors.append({'sentence_index':i,'zdanie':s,'korekta':s.replace('Yo tiene','Yo tengo'),'opis':'Czasownik tener wymaga formy tengo w pierwszej osobie.'})
        return {'reply':'¡Hola! ¿Qué te gusta hacer en tu tiempo libre?','errors':errors}

if __name__=='__main__':
    print('TEST PRZEGLĄDARKI — STUB, BEZ PRAWDZIWEGO GROQ',flush=True)
    with TemporaryDirectory(dir=Path(__file__).resolve().parent.parent/'tmp') as folder:
        uvicorn.run(create_app(Path(folder)/'browser.sqlite3',llm=BrowserStub(),dev=True),host='127.0.0.1',port=8011,access_log=False)
