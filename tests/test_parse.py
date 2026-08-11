"""Test del parsing delle pagine dei risultati (formati moderno e storico)."""

from estrattore_elezioni import parse_risultati

# Pagina comunale moderna (26/05/2019, semplificata ma fedele al formato)
HTML_MODERNO = """
<html><body>
<h3>Comunali 26/05/2019 Area ITALIA Regione TOSCANA Provincia SIENA Comune MONTEPULCIANO</h3>
<table class="dati_riepilogo">
<tr><th>Affluenza</th></tr>
<tr><td>Elettori</td><td>2.345</td><td></td></tr>
<tr><td>Votanti</td><td>1.203</td><td>51,30 %</td></tr>
</table>
<table class="dati_riepilogo">
<tr><th>Schede</th></tr>
<tr><td>Bianche</td><td>3</td></tr>
<tr><td>Non valide (bianche incl.)</td><td>9</td></tr>
</table>
<table>
<tr><th>Candidati e Liste/Gruppi</th><th></th><th></th><th>Voti</th><th>%</th><th>Seggi</th></tr>
<tr><td>BIANCHI MARIO</td><td>Eletto sind.</td><td></td><td></td><td>618</td><td>51,42</td><td></td></tr>
<tr><td></td><td>INNOVAZIONE</td><td></td><td></td><td></td><td>618</td><td>51,42</td><td>7</td></tr>
<tr><td>ROSSI LUIGI</td><td></td><td></td><td></td><td>582</td><td>48,58</td><td></td></tr>
<tr><td></td><td>UNIONE CIVICA</td><td></td><td></td><td></td><td>582</td><td>48,58</td><td>3</td></tr>
<tr><td>TOTALE</td><td>CANDIDATI</td><td></td><td></td><td>1.200</td><td></td><td></td></tr>
</table>
</body></html>
"""

# Pagina storica (08/06/1980, sindaco eletto dal consiglio: sole liste)
HTML_STORICO = """
<html><body>
<h3>Comunali 08/06/1980 Area ITALIA Regione TOSCANA Provincia SIENA Comune PIENZA</h3>
<table class="dati_riepilogo">
<tr><th>Affluenza</th></tr>
<tr><td>Elettori</td><td>1.987</td><td></td></tr>
<tr><td>Votanti</td><td>1.512</td><td>76,10 %</td></tr>
</table>
<table class="dati_riepilogo">
<tr><th>Schede</th></tr>
<tr><td>Bianche</td><td>41</td></tr>
<tr><td>Non valide (bianche incl.)</td><td>66</td></tr>
</table>
<table>
<tr><th>Liste/Gruppi</th><th>Voti</th><th>%</th><th>Seggi</th></tr>
<tr><td></td><td>DC</td><td>812</td><td>53,98</td><td>16</td></tr>
<tr><td></td><td>PSI</td><td>700</td><td>46,02</td><td>4</td></tr>
<tr><td>TOTALI</td><td></td><td>1.512</td><td></td><td>20</td></tr>
</table>
</body></html>
"""


def test_parse_moderno():
    r = parse_risultati(HTML_MODERNO)
    assert r["elettori"] == 2345
    assert r["votanti"] == 1203
    assert r["affluenza_pct"] == 51.30
    assert r["bianche"] == 3
    assert r["non_valide"] == 9
    assert len(r["candidati"]) == 2
    bianchi, rossi = r["candidati"]
    assert bianchi["candidato"] == "BIANCHI MARIO"
    assert bianchi["eletto"] is True
    assert bianchi["voti_candidato"] == 618
    assert bianchi["pct_candidato"] == 51.42
    assert bianchi["liste"][0]["lista"] == "INNOVAZIONE"
    assert bianchi["liste"][0]["seggi"] == 7
    assert rossi["eletto"] is False
    assert rossi["liste"][0]["seggi"] == 3


def test_parse_storico():
    r = parse_risultati(HTML_STORICO)
    assert r["elettori"] == 1987
    assert r["affluenza_pct"] == 76.10
    assert len(r["candidati"]) == 2
    dc, psi = r["candidati"]
    assert dc["candidato"] is None  # formato storico: solo liste
    assert dc["liste"][0]["lista"] == "DC"
    assert dc["liste"][0]["voti"] == 812
    assert dc["liste"][0]["pct"] == 53.98
    assert dc["liste"][0]["seggi"] == 16


def test_parse_pagina_vuota():
    r = parse_risultati("<html><body>nessuna consultazione</body></html>")
    assert r["elettori"] is None
    assert r["candidati"] == []
