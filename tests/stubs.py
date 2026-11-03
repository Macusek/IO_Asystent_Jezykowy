from app.llm import LLMError

class StubLLM:
    """Uniquement testowy klient. Żadnych żądań HTTP ani kluczy."""
    def __init__(self,result=None,error=None):
        self.result=result or {'reply':'¡Hola! ¿Qué te gusta hacer?','errors':[]}
        self.error=error
        self.calls=[]

    def complete(self,history,language,level,text):
        self.calls.append((history,language,level,text))
        if self.error:
            raise LLMError(self.error)
        return self.result
