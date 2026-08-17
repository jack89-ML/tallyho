"""Test della cache dei form (SQLite, ~/.cache/tallyho/)."""

import os
import time

import pytest
import requests

from tallyho.cache import CachedSession, _percorso_db, cache_leggi, cache_scrivi


@pytest.fixture(autouse=True)
def cache_tmp(tmp_path, monkeypatch):
    """Dirige la cache su una directory temporanea per ogni test."""
    monkeypatch.setenv("TALLYHO_CACHE_DIR", str(tmp_path / "cache"))
    yield


def test_percorso_db_usa_env():
    assert "cache.db" in _percorso_db()
    assert "tmp" in _percorso_db() or "cache" in _percorso_db()


def test_scrittura_e_lettura():
    cache_scrivi("http://esempio.it/pagina", "<html>ciao</html>")
    assert cache_leggi("http://esempio.it/pagina", ttl=3600) == \
        "<html>ciao</html>"


def test_url_non_presente():
    assert cache_leggi("http://esempio.it/mai_scaricata", ttl=3600) == ""


def test_ttl_scaduto():
    cache_scrivi("http://esempio.it/vecchia", "<html>vecchio</html>")
    # ttl negativo/zero: mai servita
    assert cache_leggi("http://esempio.it/vecchia", ttl=0) == ""
    # ttl molto piccolo (1ns): scaduta
    assert cache_leggi("http://esempio.it/vecchia", ttl=1e-9) == ""


def test_ttl_lungo_serve():
    cache_scrivi("http://esempio.it/recente", "<html>nuovo</html>")
    assert cache_leggi("http://esempio.it/recente", ttl=10 ** 9) == \
        "<html>nuovo</html>"


def test_sovrascrittura():
    cache_scrivi("http://esempio.it/x", "<html>prima</html>")
    cache_scrivi("http://esempio.it/x", "<html>dopo</html>")
    assert cache_leggi("http://esempio.it/x", ttl=3600) == "<html>dopo</html>"


class _FakeRisposta:
    def __init__(self, testo, status=200):
        self.text = testo
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_cached_session_serve_da_cache(monkeypatch):
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        return _FakeRisposta(f"<html>{url}</html>")

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=3600)
    prima = sessione.get("http://esempio.it/a")
    seconda = sessione.get("http://esempio.it/a")
    assert prima.text == seconda.text == "<html>http://esempio.it/a</html>"
    # la rete è stata toccata UNA volta: la seconda risposta viene dalla cache
    assert len(chiamate) == 1
    assert sessione._colpi == 1
    assert sessione._mancati == 1


def test_cached_session_ttl_zero_sempre_rete(monkeypatch):
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        return _FakeRisposta("<html>x</html>")

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=0)  # cache disabilitata
    sessione.get("http://esempio.it/b")
    sessione.get("http://esempio.it/b")
    assert len(chiamate) == 2


def test_statistiche():
    sessione = CachedSession(ttl=0)
    assert "nessuna richiesta" in sessione.statistiche()


# --------------------------------------------------------------------------
# Retry con backoff esponenziale (errori transitori, niente 4xx)
# --------------------------------------------------------------------------

class _RispostaErrore:
    """Risposta finta che solleva un vero HTTPError su raise_for_status()."""

    def __init__(self, status, testo="<html>x</html>"):
        self.status_code = status
        self.text = testo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} error", response=self)


def test_retry_500_poi_200(monkeypatch):
    """Un 5xx transitorio viene ritentato: il secondo tentativo va a buon
    fine e il contatore dei retry è 1."""
    stati = iter([500, 200])
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        return _RispostaErrore(next(stati))

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=0, retry_backoff=0)  # attesa nulla nei test
    risposta = sessione.get("http://esempio.it/x")
    assert risposta.status_code == 200
    assert len(chiamate) == 2
    assert sessione._retry == 1


def test_retry_esaurisce_i_tentativi(monkeypatch):
    """Tre errori consecutivi -> solleva dopo max_retries tentativi extra."""
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        return _RispostaErrore(500)

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=0, max_retries=3, retry_backoff=0)
    with pytest.raises(requests.exceptions.HTTPError):
        sessione.get("http://esempio.it/x")
    # 1 tentativo iniziale + 3 retry = 4 chiamate totali
    assert len(chiamate) == 4
    assert sessione._retry == 3


def test_retry_nessun_retry_su_4xx(monkeypatch):
    """Gli errori 4xx sono permanenti: nessun retry, solleva subito."""
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        return _RispostaErrore(404)

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=0, retry_backoff=0)
    with pytest.raises(requests.exceptions.HTTPError):
        sessione.get("http://esempio.it/x")
    assert len(chiamate) == 1
    assert sessione._retry == 0


def test_retry_su_connection_error(monkeypatch):
    """Anche ConnectionError (rete giù) viene ritentato."""
    tentativi = [requests.exceptions.ConnectionError("boom"),
                 requests.exceptions.ConnectionError("boom")]
    chiamate = []

    def finto_get(self, url, **kwargs):
        chiamate.append(url)
        if tentativi:
            raise tentativi.pop(0)
        return _RispostaErrore(200)

    monkeypatch.setattr("requests.Session.get", finto_get)
    sessione = CachedSession(ttl=0, retry_backoff=0)
    risposta = sessione.get("http://esempio.it/x")
    assert risposta.status_code == 200
    assert len(chiamate) == 3
    assert sessione._retry == 2
