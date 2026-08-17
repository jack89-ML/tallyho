"""Test di trova_comune: discesa dinamica della gerarchia (fino a 5 livelli)
con una FakeSession che risponde per-URL (nessuna rete)."""

from tallyho import parse_risultati, trova_comune

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


def _risposte_regionali():
    """Regionali: la pagina dopo la selezione della regione contiene GIÀ i
    risultati (early-return) — nessuna discesa per comune."""
    return [
        ("lev1=", HTML_RISULTATI),  # dopo la regione: pagina dei risultati
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=R&dtel=", _select(
            "sel_aree", "ne0", [("I-lev00-levsut00-msN-tpeA", "ITALIA")],
            page_path="index.php?tpel=R&dtel=12/02/2023&es0=S")),
    ]


def test_trova_comune_regionali_early_return():
    """Per le regionali (R) il livello regione È GIÀ la pagina dei risultati:
    trova_comune deve fermarsi lì e replicare il contesto per comune, senza
    tentare una discesa per-comune (regressione possibile nel refactor della
    catena condivisa)."""
    sess = FakeSessionPerUrl(_risposte_regionali())
    html, ctx = trova_comune(sess, "12/02/2023", "ROMA", "R", None,
                             "LAZIO", ("ROMA",))
    assert html == HTML_RISULTATI
    assert ctx["regione"] == "LAZIO"
    assert ctx["provincia"] == ""
    assert ctx["comune"].upper() == "ROMA"
    # data, area, regione = 3 richieste: nessuna discesa fino al comune
    assert len(sess.urls) == 3


def test_trova_comune_regione_non_trovata():
    # nessuna regione/circoscrizione corrisponde -> (None, None)
    sess = FakeSessionPerUrl(_risposte_comunali())
    html, ctx = trova_comune(sess, "03/10/2021", "AFFILE", "G", None,
                             "LOMBARDIA", ("ROMA",))
    assert html is None
    assert ctx is None


# ---------------------------------------------------------------------------
# Regressione: comune assente al livello finale -> NON_VOTATO (mai i dati di
# un altro comune, es. ROMA al posto di AFFILE).
# ---------------------------------------------------------------------------

def _risposte_comune_assente():
    """Comunali con il livello comune che NON contiene il target: ci sono
    ROMA e MILANO ma non AFFILE."""
    return [
        ("lev3=", HTML_RISULTATI),
        ("lev2=", _select("sel_sezione4", "ne3", [
            ("58091-lev358091", "ROMA"),
            ("15146-lev315146", "MILANO"),
        ])),
        ("lev1=", _select("sel_sezione3", "ne2", [("58-lev258", "ROMA")])),
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=G&dtel=", _select(
            "sel_aree", "ne0", [("I-lev00-levsut00-msN-tpeA", "ITALIA")],
            page_path="index.php?tpel=G&dtel=03/10/2021&es0=S")),
    ]


def test_comune_assente_al_livello_finale():
    # regressione: il comune target non è tra le opzioni del livello comune
    # -> (None, None) -> NON_VOTATO, NON i dati di ROMA etichettati AFFILE
    sess = FakeSessionPerUrl(_risposte_comune_assente())
    html, ctx = trova_comune(sess, "03/10/2021", "AFFILE", "G", None,
                             "LAZIO", ("ROMA",))
    assert html is None
    assert ctx is None


def test_record_comune_corretto():
    # il record/CSV deve riportare il comune RICHIESTO, mai un altro:
    # 1) comune presente -> ctx["comune"] == comune richiesto;
    # 2) comune assente -> html None (nessun record, NON_VOTATO), mai i dati
    #    di un altro comune etichettati col comune richiesto.
    sess = FakeSessionPerUrl(_risposte_comunali())
    html, ctx = trova_comune(sess, "03/10/2021", "AFFILE", "G", None,
                             "LAZIO", ("ROMA",))
    assert html is not None
    assert ctx["comune"].upper() == "AFFILE"

    sess2 = FakeSessionPerUrl(_risposte_comune_assente())
    html2, ctx2 = trova_comune(sess2, "03/10/2021", "AFFILE", "G", None,
                               "LAZIO", ("ROMA",))
    assert html2 is None


# ---------------------------------------------------------------------------
# Referendum: area ITALIA (non ESTERO) + pagina SI/NO riconosciuta.
# ---------------------------------------------------------------------------

HTML_REFERENDUM = """
<html><body>
<h3>Referendum 12/06/2022 Area ITALIA Regione LAZIO Provincia ROMA Comune AFFILE</h3>
<div class="dati_referendum_titolo_quesito">1. Abrogazione del Testo unico delle disposizioni in materia di incandidabilità</div>
<table><tr><th>Elettori</th><td>1.217</td></tr></table>
<table><tr><th colspan="3">Affluenza</th></tr>
<tr><td>Votanti</td><td>251</td></tr>
<tr><td>%</td><td>20,62</td></tr></table>
<table><tr><th colspan="3">Schede</th></tr>
<tr><td>Valide</td><td>240</td></tr>
<tr><td>Schede bianche</td><td>5</td></tr>
<tr><td>Schede non valide (bianche incl.)</td><td>11</td></tr></table>
<table class="dati"><tr><th>SI</th><th>NO</th></tr>
<tr><td>150</td><td>90</td></tr>
<tr><td>62,50%</td><td>37,50%</td></tr></table>
<div class="dati_referendum_titolo_quesito">2. Abrogazione di norme in materia di elezioni dei componenti degli organi</div>
<table><tr><th>Elettori</th><td>1.217</td></tr></table>
<table><tr><th colspan="3">Affluenza</th></tr>
<tr><td>Votanti</td><td>251</td></tr>
<tr><td>%</td><td>20,62</td></tr></table>
<table><tr><th colspan="3">Schede</th></tr>
<tr><td>Valide</td><td>238</td></tr>
<tr><td>Schede bianche</td><td>7</td></tr>
<tr><td>Schede non valide (bianche incl.)</td><td>13</td></tr></table>
<table class="dati"><tr><th>SI</th><th>NO</th></tr>
<tr><td>120</td><td>118</td></tr>
<tr><td>50,42%</td><td>49,58%</td></tr></table>
</body></html>
"""


def _risposte_referendum():
    """data -> area (ESTERO/ITALIA+ESTERO/ITALIA) -> regione -> provincia ->
    comune -> pagina referendum (SI/NO)."""
    return [
        ("lev3=", HTML_REFERENDUM),
        ("lev2=", _select("sel_sezione4", "ne3",
                          [("53012-lev353012", "AFFILE")])),
        ("lev1=", _select("sel_sezione3", "ne2", [("58-lev258", "ROMA")])),
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=F&dtel=", _select(
            "sel_aree", "ne0", [
                ("E-lev00-levsut00-msN-tpeE", "ESTERO"),
                ("IE-lev00-levsut00-msN-tpeT", "ITALIA+ESTERO"),
                ("I-lev00-levsut00-msN-tpeA", "ITALIA"),
            ],
            page_path="index.php?tpel=F&dtel=12/06/2022&es0=S")),
    ]


def test_scelta_area_referendum_italia():
    # sel_aree = [ESTERO, ITALIA+ESTERO, ITALIA]: deve scegliere ITALIA
    # (tpa=I), NON l'area 0 (ESTERO). La discesa si ferma subito (regione
    # LOMBARDIA assente) ma l'area scelta è già visibile nella URL.
    sess = FakeSessionPerUrl([
        ("tpa=", _select("sel_sezione2", "ne1", [("12-lev112", "LAZIO")])),
        ("tpel=F&dtel=", _select(
            "sel_aree", "ne0", [
                ("E-lev00-levsut00-msN-tpeE", "ESTERO"),
                ("IE-lev00-levsut00-msN-tpeT", "ITALIA+ESTERO"),
                ("I-lev00-levsut00-msN-tpeA", "ITALIA"),
            ],
            page_path="index.php?tpel=F&dtel=12/06/2022&es0=S")),
    ])
    html, ctx = trova_comune(sess, "12/06/2022", "AFFILE", "F", None,
                             "LOMBARDIA", ("ROMA",))
    assert html is None
    # la richiesta dell'area (la seconda) punta all'area ITALIA, non ESTERO
    assert "&tpa=I&" in sess.urls[1]
    assert "&tpa=E&" not in sess.urls[1]


def test_referendum_end_to_end():
    # navigazione completa referendum -> pagina SI/NO -> parse_risultati
    # produce i quesiti (verifica anche l'instradamento del parser).
    sess = FakeSessionPerUrl(_risposte_referendum())
    html, ctx = trova_comune(sess, "12/06/2022", "AFFILE", "F", None,
                             "LAZIO", ("ROMA",))
    assert html == HTML_REFERENDUM
    assert ctx["comune"].upper() == "AFFILE"
    assert ctx["regione"] == "LAZIO"
    assert ctx["provincia"] == "ROMA"
    parsed = parse_risultati(html)
    assert "quesiti" in parsed
    assert len(parsed["quesiti"]) == 2
    q = parsed["quesiti"][0]
    assert q["si"] == {"voti": 150, "pct": 62.50}
    assert q["no"] == {"voti": 90, "pct": 37.50}
    assert parsed["quesiti"][1]["si"] == {"voti": 120, "pct": 50.42}

