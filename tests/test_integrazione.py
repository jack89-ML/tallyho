"""Test d'integrazione: una sola richiesta reale al sito (esclusi di default).

Esegui esplicitamente con:  pytest -m integration
(il `pytest` nudo li salta grazie ad `addopts = "-m 'not integration'"`).
"""

import pytest
import requests

from tallyho.costanti import BASE, UA
from tallyho.navigazione import leggi_date


@pytest.mark.integration
def test_sito_risponde_e_elenca_date():
    # una sola richiesta reale (equivalente a `tallyho --elenca date`):
    # verifica che il sito risponda e che le date siano ancora leggibili.
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    r = sess.get(f"{BASE}?tpel=G", timeout=30)
    r.raise_for_status()
    date = leggi_date(r.text)
    assert date, "nessuna data trovata nella pagina (formato del sito cambiato?)"
