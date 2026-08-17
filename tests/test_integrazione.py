"""Test d'integrazione live: chiamate REALI al sito (esclusi di default).

Coprono i 5 tipi principali di elezione (G/R/F/E/P). Esegui esplicitamente:

    pytest -m integration

Il `pytest` nudo li salta grazie ad `addopts = "-m 'not integration'"`.

Attenzione: richiedono rete verso elezionistorico.interno.gov.it. Se il sito
è irraggiungibile o cambia formato, falliscono onestamente (nessuno skip
silenzioso). Le estrazioni sono volutamente leggere: una data sola, un comune
solo, con una pausa breve tra le chiamate per rispetto del server.
"""

import time

import pytest
import requests

from tallyho.costanti import BASE, UA
from tallyho.navigazione import leggi_date, trova_comune
from tallyho.parsing import parse_risultati

# Pausa tra una richiesta e l'altra: rispetto del server (niente burst).
PAUSA = 0.5


def _sessione():
    """Sessione HTTP con lo User-Agent del browser (come fa la CLI)."""
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    return sess


def _date_del_tipo(tipo):
    """Date disponibili per un tipo di elezione (una sola richiesta reale)."""
    sess = _sessione()
    r = sess.get(f"{BASE}?tpel={tipo}", timeout=30)
    r.raise_for_status()
    return leggi_date(r.text)


@pytest.mark.integration
def test_sito_risponde_e_elenca_date_comunali():
    # una sola richiesta reale (equivalente a `tallyho --elenca date`):
    # verifica che il sito risponda e che le date siano ancora leggibili.
    date = _date_del_tipo("G")
    assert date, "nessuna data trovata nella pagina (formato del sito cambiato?)"


@pytest.mark.integration
def test_date_regionali():
    # regionali (R): il sito deve esporre almeno una data.
    time.sleep(PAUSA)
    date = _date_del_tipo("R")
    assert date, "nessuna data per tpel=R (formato del sito cambiato?)"


@pytest.mark.integration
def test_date_europee():
    # europee (E): il sito deve esporre almeno una data.
    time.sleep(PAUSA)
    date = _date_del_tipo("E")
    assert date, "nessuna data per tpel=E (formato del sito cambiato?)"


@pytest.mark.integration
def test_date_provinciali():
    # provinciali (P): il sito deve esporre almeno una data.
    time.sleep(PAUSA)
    date = _date_del_tipo("P")
    assert date, "nessuna data per tpel=P (formato del sito cambiato?)"


@pytest.mark.integration
def test_date_referendum():
    # referendum (F): il sito deve esporre almeno una data.
    time.sleep(PAUSA)
    date = _date_del_tipo("F")
    assert date, "nessuna data per tpel=F (formato del sito cambiato?)"


@pytest.mark.integration
def test_estrazione_comunali_roma():
    # estrazione di UNA data su un comune noto: almeno un record con candidati.
    time.sleep(PAUSA)
    sess = _sessione()
    html, ctx = trova_comune(sess, "03/10/2021", "ROMA", "G", None,
                             "LAZIO", ("ROMA",))
    assert html is not None, "ROMA non trovata per le comunali del 03/10/2021"
    assert ctx is not None
    assert ctx["comune"].upper() == "ROMA"
    parsed = parse_risultati(html)
    assert parsed["candidati"], "nessun candidato estratto per ROMA 03/10/2021"


@pytest.mark.integration
def test_estrazione_referendum_affile():
    # referendum 12/06/2022 su AFFILE: 5 quesiti, con voti SI/NO.
    time.sleep(PAUSA)
    sess = _sessione()
    html, ctx = trova_comune(sess, "12/06/2022", "AFFILE", "F", None,
                             "LAZIO", ("ROMA",))
    assert html is not None, "AFFILE non trovata per il referendum 12/06/2022"
    assert ctx is not None
    assert ctx["comune"].upper() == "AFFILE"
    parsed = parse_risultati(html)
    quesiti = parsed["quesiti"]
    assert quesiti, "nessun quesito referendario estratto per AFFILE 12/06/2022"
    assert len(quesiti) == 5, f"attesi 5 quesiti, trovati {len(quesiti)}"
