"""Cache dei form decodificati in SQLite (~/.cache/tallyho/cache.db).

Memorizza le pagine HTML scaricate per URL, così le stesse pagine del
form (date, aree, regioni, province...) non vengono riscaricate a ogni
run: utile per dataset grandi (decine di migliaia di richieste) e per
tollerare brevi indisponibilità del sito.

La cache è trasparente: si usa `CachedSession` al posto di
`requests.Session` (stessa interfaccia), attivata solo dalla CLI
(`--cache`/`--cache-ttl`). I test restano invariati perché usano
FakeSession, non questa classe.
"""

import os
import sqlite3
import time

import requests


def _percorso_db() -> str:
    base = os.environ.get("TALLYHO_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "tallyho")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "cache.db")


def _apri_db():
    db = sqlite3.connect(_percorso_db())
    db.execute(
        "CREATE TABLE IF NOT EXISTS pagine ("
        " url TEXT PRIMARY KEY, html TEXT, ts REAL)"
    )
    return db


def cache_leggi(url: str, ttl: float) -> str:
    """Ritorna l'HTML in cache se presente e non scaduto, altrimenti ''."""
    if ttl <= 0:
        return ""
    db = _apri_db()
    try:
        riga = db.execute(
            "SELECT html, ts FROM pagine WHERE url = ?", (url,)
        ).fetchone()
    finally:
        db.close()
    if not riga:
        return ""
    html, ts = riga
    if time.time() - ts > ttl:
        return ""
    return html


def cache_scrivi(url: str, html: str) -> None:
    db = _apri_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO pagine (url, html, ts) VALUES (?, ?, ?)",
            (url, html, time.time()),
        )
        db.commit()
    finally:
        db.close()


class _RispostaCache:
    """Risposta finta compatibile con l'uso che ne fa il codice
    (`.text` e `.raise_for_status()`)."""

    def __init__(self, testo: str):
        self.text = testo
        self.status_code = 200

    def raise_for_status(self):
        return None


class CachedSession(requests.Session):
    """requests.Session che serve le pagine del form dalla cache SQLite.

    `ttl` = secondi di validità di una pagina (default 7 giorni: le
    pagine del form cambiano solo con le elezioni). `ttl=0` disabilita
    la cache (comportamento identico a requests.Session).
    """

    def __init__(self, ttl: float = 7 * 24 * 3600):
        super().__init__()
        self.ttl = ttl
        self._colpi = 0
        self._mancati = 0

    def get(self, url, **kwargs):  # type: ignore[override]  # risposta finta o reale
        if self.ttl > 0:
            from_cache = cache_leggi(url, self.ttl)
            if from_cache:
                self._colpi += 1
                return _RispostaCache(from_cache)
            self._mancati += 1
        risposta = super().get(url, **kwargs)
        if self.ttl > 0 and risposta.status_code == 200:
            cache_scrivi(url, risposta.text)
        return risposta

    def statistiche(self) -> str:
        tot = self._colpi + self._mancati
        if not tot:
            return "cache: nessuna richiesta"
        return f"cache: {self._colpi}/{tot} richieste servite da cache " \
               f"({100 * self._colpi / tot:.0f}%)"
