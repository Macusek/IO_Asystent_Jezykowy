import httpx
import pytest

@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    """Przypadkowe wywołanie rzeczywistej sieci HTTP natychmiast oblewa test."""
    def blocked(*args,**kwargs):
        raise AssertionError('Test próbował połączyć się z prawdziwą siecią.')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',blocked)
