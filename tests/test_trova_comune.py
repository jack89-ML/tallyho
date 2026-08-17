"""Test di trova_comune: discesa dinamica della gerarchia (fino a 5 livelli)
con una FakeSession che risponde per-URL (nessuna rete)."""

from tallyho import trova_comune

HTML_RISULTATI = """
<html><body>
<h3>Comunali 03/10/2021</h3>
<table><tr><th>Affluenza</th></tr><tr><td>Elettori</td><td>100</td></tr></table>
<table><tr><th>Candidati e Liste/Gruppi</th></tr><tr><td>ROSSI</td></tr></table>
</body></html>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSessionPerUrl:
    """Sessione finta che risponde in base a una lista di
    (sottostringa_url, html): ritorna la prima risposta la cui chiave è
    contenuta nella URL richiesta (le chiavi più specifiche vanno per prime)."""

    def __init__(self, risposte):
        self.risposte = risposte
        self.urls = []

    def get(self, url, timeout=30):
        self.urls.append(url)
        for chiave, html in self.risposte:
            if chiave in url:
                return FakeResponse(html)
        raise AssertionError(f"URL non prevista dalla FakeSession: {url}")


def _select(nome, var, opzioni, page_path="index.php"):
    """Costruisce una pagina con un solo <select> e le sue <option>."""
    opt = "".join(f'<option value="{v}">{t}</option>' for v, t in opzioni)
    return (f'<html><body><select name="{nome}" '
            f'onchange="carica_pagina(\'{page_path}\',\'{var}\','
            f'this.options[this.selectedIndex].value);">{opt}</select>'
            f'</body></html>')


def _risposte_comunali():
    """data -> area -> regione -> provincia -> comune -> risultati (4 livelli)."""
    return [
        ("lev3=", HTML_RISULTATI),
        ("lev2=", _select("sel_sezione4", "ne3",
                          [("53012-lev353012", "AFFILE")])),
        ("lev1=", _select("sel_sezione3", "ne2", [("58-lev258", "ROMA")])),
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=G&dtel=", _select(
            "sel_aree", "ne0", [("I-lev00-levsut00-msN-tpeA", "ITALIA")],
            page_path="index.php?tpel=G&dtel=03/10/2021&es0=S")),
    ]


def _risposte_europee():
    """data -> area -> circoscrizione -> regione -> provincia -> comune (5)."""
    return [
        ("lev4=", HTML_RISULTATI),
        ("lev3=", _select("sel_sezione5", "ne4",
                          [("53012-lev453012", "AFFILE")])),
        ("lev2=", _select("sel_sezione4", "ne3", [("58-lev358", "ROMA")])),
        ("lev1=", _select("sel_sezione3", "ne2", [("12-lev212", "LAZIO")])),
        ("tpa=", _select("sel_sezione2", "ne1",
                         [("4-lev14", "ITALIA MERIDIONALE")])),
        ("tpel=E&dtel=", _select(
            "sel_aree", "ne0", [("I-lev00-levsut00-msN-tpeA", "ITALIA")],
            page_path="index.php?tpel=E&dtel=26/05/2019&es0=S")),
    ]


def _risposte_provinciali():
    """data -> area -> regione -> provincia -> collegio -> comune (5)."""
    return [
        ("lev4=", HTML_RISULTATI),
        ("lev3=", _select("sel_sezione5", "ne4",
                          [("53012-lev453012", "AFFILE")])),
        ("lev2=", _select("sel_sezione4", "ne3",
                          [("col-lev3col", "COLLEGIO 1")])),
        ("lev1=", _select("sel_sezione3", "ne2", [("58-lev258", "ROMA")])),
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=P&dtel=", _select(
            "sel_aree", "ne0", [("I-lev00-levsut00-msN-tpeA", "ITALIA")],
            page_path="index.php?tpel=P&dtel=12/05/2019&es0=S")),
    ]


def test_trova_comune_comunali_4_livelli():
    sess = FakeSessionPerUrl(_risposte_comunali())
    html, ctx = trova_comune(sess, "03/10/2021", "AFFILE", "G", None,
                             "LAZIO", ("ROMA",))
    assert html == HTML_RISULTATI
    assert ctx["regione"] == "LAZIO"
    assert ctx["provincia"] == "ROMA"
    assert ctx["comune"].upper() == "AFFILE"
    # data, area, regione, provincia, comune = 5 richieste
    assert len(sess.urls) == 5
    assert "tpel=G" in sess.urls[0]


def test_trova_comune_europee_5_livelli():
    sess = FakeSessionPerUrl(_risposte_europee())
    html, ctx = trova_comune(sess, "26/05/2019", "AFFILE", "E", None,
                             "ITALIA MERIDIONALE", ("ROMA",))
    assert html == HTML_RISULTATI
    assert ctx["regione"] == "ITALIA MERIDIONALE"
    assert ctx["provincia"] == "ROMA"
    assert ctx["comune"].upper() == "AFFILE"
    # data, area, circoscrizione, regione, provincia, comune = 6 richieste
    assert len(sess.urls) == 6
    # la discesa raggiunge il 5° livello (sel_sezione5 -> lev4)
    assert any("lev4=" in u for u in sess.urls)


def test_trova_comune_provinciali_5_livelli():
    sess = FakeSessionPerUrl(_risposte_provinciali())
    html, ctx = trova_comune(sess, "12/05/2019", "AFFILE", "P", None,
                             "LAZIO", ("ROMA",))
    assert html == HTML_RISULTATI
    assert ctx["regione"] == "LAZIO"
    assert ctx["provincia"] == "ROMA"
    assert ctx["comune"].upper() == "AFFILE"
    assert len(sess.urls) == 6
    assert any("lev4=" in u for u in sess.urls)


def test_trova_comune_regione_non_trovata():
    # nessuna regione/circoscrizione corrisponde -> (None, None)
    sess = FakeSessionPerUrl(_risposte_comunali())
    html, ctx = trova_comune(sess, "03/10/2021", "AFFILE", "G", None,
                             "LOMBARDIA", ("ROMA",))
    assert html is None
    assert ctx is None
