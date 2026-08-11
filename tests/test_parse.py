"""Test del parsing delle pagine dei risultati (formati moderno e storico)."""

from estrattore_elezioni import parse_risultati

# Pagina comunale moderna (14/05/2023 Savelli, semplificata ma fedele)
HTML_MODERNO = """
<html><body>
<h3>Comunali 14/05/2023 Area ITALIA Regione CALABRIA Provincia CROTONE Comune SAVELLI</h3>
<table class="dati_riepilogo">
<tr><th>Affluenza</th></tr>
<tr><td>Elettori</td><td>1.662</td><td></td></tr>
<tr><td>Votanti</td><td>819</td><td>49,28 %</td></tr>
</table>
<table class="dati_riepilogo">
<tr><th>Schede</th></tr>
<tr><td>Bianche</td><td>3</td></tr>
<tr><td>Non valide (bianche incl.)</td><td>9</td></tr>
</table>
<table>
<tr><th>Candidati e Liste/Gruppi</th><th></th><th></th><th>Voti</th><th>%</th><th>Seggi</th></tr>
<tr><td>SPINA FRANCESCO</td><td>Eletto sind.</td><td></td><td></td><td>415</td><td>51,23</td><td></td></tr>
<tr><td></td><td>RICOMINCIAMO</td><td></td><td></td><td></td><td>415</td><td>51,23</td><td>7</td></tr>
<tr><td>FRONTERA DOMENICO</td><td></td><td></td><td></td><td>395</td><td>48,77</td><td></td></tr>
<tr><td></td><td>L'ALVEARE SAVELLI A LAVORO</td><td></td><td></td><td></td><td>395</td><td>48,77</td><td>3</td></tr>
<tr><td>TOTALE</td><td>CANDIDATI</td><td></td><td></td><td>810</td><td></td><td></td></tr>
</table>
</body></html>
"""

# Pagina storica (07/06/1970, sindaco eletto dal consiglio: sole liste)
HTML_STORICO = """
<html><body>
<h3>Comunali 07/06/1970 Area ITALIA Regione CALABRIA Provincia COSENZA Comune CAMPANA</h3>
<table class="dati_riepilogo">
<tr><th>Affluenza</th></tr>
<tr><td>Elettori</td><td>2.339</td><td></td></tr>
<tr><td>Votanti</td><td>1.778</td><td>76,02 %</td></tr>
</table>
<table class="dati_riepilogo">
<tr><th>Schede</th></tr>
<tr><td>Bianche</td><td>41</td></tr>
<tr><td>Non valide (bianche incl.)</td><td>66</td></tr>
</table>
<table>
<tr><th>Liste/Gruppi</th><th>Voti</th><th>%</th><th>Seggi</th></tr>
<tr><td></td><td>DC</td><td>923</td><td>54,23</td><td>16</td></tr>
<tr><td></td><td>ETEROGENEE</td><td>779</td><td>45,77</td><td>4</td></tr>
<tr><td>TOTALI</td><td></td><td>1.702</td><td></td><td>20</td></tr>
</table>
</body></html>
"""


def test_parse_moderno():
    r = parse_risultati(HTML_MODERNO)
    assert r["elettori"] == 1662
    assert r["votanti"] == 819
    assert r["affluenza_pct"] == 49.28
    assert r["bianche"] == 3
    assert r["non_valide"] == 9
    assert len(r["candidati"]) == 2
    spina, frontera = r["candidati"]
    assert spina["candidato"] == "SPINA FRANCESCO"
    assert spina["eletto"] is True
    assert spina["voti_candidato"] == 415
    assert spina["pct_candidato"] == 51.23
    assert spina["liste"][0]["lista"] == "RICOMINCIAMO"
    assert spina["liste"][0]["seggi"] == 7
    assert frontera["eletto"] is False
    assert frontera["liste"][0]["seggi"] == 3


def test_parse_storico():
    r = parse_risultati(HTML_STORICO)
    assert r["elettori"] == 2339
    assert r["affluenza_pct"] == 76.02
    assert len(r["candidati"]) == 2
    dc, eterogenee = r["candidati"]
    assert dc["candidato"] is None  # formato storico: solo liste
    assert dc["liste"][0]["lista"] == "DC"
    assert dc["liste"][0]["voti"] == 923
    assert dc["liste"][0]["pct"] == 54.23
    assert dc["liste"][0]["seggi"] == 16


def test_parse_pagina_vuota():
    r = parse_risultati("<html><body>nessuna consultazione</body></html>")
    assert r["elettori"] is None
    assert r["candidati"] == []
