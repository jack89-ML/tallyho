"""Test della navigazione: lettura select/onchange/date, discesa dei livelli
e riconoscimento della pagina dei risultati (senza rete)."""

from tallyho import (leggi_date, leggi_onchange, leggi_select,
                     pagina_ha_risultati, scendi_livello)

BASE = "https://elezionistorico.interno.gov.it/index.php"

# Replica fedele del formato del form del sito (value = testo per le date)
HTML_SELECT = """
<html><body>
<select name="sel_date">
  <option value="0">-- scegli --</option>
  <option value="03/10/2021">03/10/2021</option>
  <option value="26/05/2019">26/05/2019</option>
</select>
</body></html>
"""

HTML_ONCHANGE = """
<html><body>
<select name="sel_aree" onchange="carica_pagina('index.php?tpel=G&dtel=03/10/2021&es0=S','ne0',this.options[this.selectedIndex].value);">
  <option value="I-lev00-levsut00-msN-tpeA">ITALIA</option>
</select>
</body></html>
"""

HTML_RISULTATI = """
<html><body>
<table><tr><th>Affluenza</th></tr><tr><td>Elettori</td><td>100</td></tr></table>
<table><tr><th>Candidati e Liste/Gruppi</th></tr><tr><td>ROSSI</td></tr></table>
</body></html>
"""

HTML_SOLO_AFFLUENZA = """
<html><body>
<table><tr><th>Affluenza</th></tr><tr><td>Elettori</td><td>100</td></tr></table>
</body></html>
"""

HTML_SENZA_RISULTATI = """
<html><body>
<select name="sel_sezione2">
  <option value="12-lev112">LAZIO</option>
</select>
</body></html>
"""


class FakeResponse:
    """Risposta HTTP minima: .text e .raise_for_status()."""

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSession:
    """Sessione finta: registra le URL richieste e ritorna testo fisso."""

    def __init__(self, text):
        self.text = text
        self.urls = []

    def get(self, url, timeout=30):
        self.urls.append(url)
        return FakeResponse(self.text)


def test_leggi_select():
    out = leggi_select(HTML_SELECT, "sel_date")
    assert out == [("03/10/2021", "03/10/2021"), ("26/05/2019", "26/05/2019")]


def test_leggi_select_assente():
    assert leggi_select("<html></html>", "sel_date") == []


def test_leggi_onchange():
    pp, pv = leggi_onchange(HTML_ONCHANGE, "sel_aree")
    assert pp == "index.php?tpel=G&dtel=03/10/2021&es0=S"
    assert pv == "ne0"


def test_leggi_onchange_assente():
    assert leggi_onchange("<html></html>", "sel_aree") == (None, None)


def test_leggi_date():
    assert leggi_date(HTML_SELECT) == ["03/10/2021", "26/05/2019"]


def test_scendi_livello_opzione():
    sess = FakeSession("<html>risultati</html>")
    out = scendi_livello(sess, "index.php?tpel=G", "ne1", "12-lev112")
    assert out == "<html>risultati</html>"
    assert sess.urls[0] == BASE + "?tpel=G&ne1=12&lev1=12"


def test_scendi_livello_area():
    sess = FakeSession("<html>risultati</html>")
    out = scendi_livello(sess, "index.php?tpel=G&dtel=03/10/2021&es0=S",
                         "tpa", "I-lev00-levsut00-msN-tpeA")
    assert out == "<html>risultati</html>"
    assert sess.urls[0] == (BASE + "?tpel=G&dtel=03/10/2021&es0=S"
                            "&tpa=I&lev0=0&levsut0=0&ms=N&tpe=A")


def test_pagina_ha_risultati_si():
    assert pagina_ha_risultati(HTML_RISULTATI) is True


def test_pagina_ha_risultati_no():
    assert pagina_ha_risultati(HTML_SENZA_RISULTATI) is False


def test_pagina_ha_risultati_solo_affluenza():
    # affluenza presente ma nessuna tabella candidati/liste -> non è la
    # pagina finale dei risultati
    assert pagina_ha_risultati(HTML_SOLO_AFFLUENZA) is False


HTML_REFERENDUM = """
<html><body>
<div class="dati_referendum_titolo_quesito">Quesito 1</div>
<table><tr><th>SI</th><th>NO</th></tr><tr><td>150</td><td>90</td></tr></table>
</body></html>
"""


def test_pagina_ha_risultati_referendum():
    # pagina referendum: div del quesito + tabella SI/NO (niente candidati)
    assert pagina_ha_risultati(HTML_REFERENDUM) is True


def test_pagina_ha_risultati_referendum_solo_tabella_si_no():
    # anche senza il div del quesito, una tabella con colonne SI/NO è una
    # pagina di risultati (referendum)
    html = ("<html><body><table><tr><th>SI</th><th>NO</th></tr>"
            "<tr><td>150</td><td>90</td></tr></table></body></html>")
    assert pagina_ha_risultati(html) is True
