"""Test del parsing delle pagine dei risultati (formati moderno e storico)."""

from pathlib import Path

import pytest

from tallyho import (parse_affluenza, parse_candidati_regionali,
                     parse_referendum, parse_risultati, parse_schede,
                     rileva_turno)

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


def test_parse_affluenza_cella_non_numerica():
    # cella non numerica (es. "N.D.") -> nessun crash, campo a None
    tabelle = [
        [
            ["Affluenza"],
            ["Elettori", "N.D.", ""],
            ["Votanti", "1.203", "51,30 %"],
        ],
    ]
    out = parse_affluenza(tabelle)
    assert out["elettori"] is None
    assert out["votanti"] == 1203
    assert out["affluenza_pct"] == 51.30


def test_parse_affluenza_fallback():
    # percentuale assente -> calcolata da votanti/elettori
    tabelle = [
        [["Affluenza"], ["Elettori", "1.000", ""], ["Votanti", "500", ""]],
    ]
    out = parse_affluenza(tabelle)
    assert out["elettori"] == 1000
    assert out["votanti"] == 500
    assert out["affluenza_pct"] == 50.0


def test_parse_affluenza_fallback_senza_elettori():
    # niente elettori -> nessun calcolo, resta None (mai divisione per zero)
    tabelle = [
        [["Affluenza"], ["Elettori", "0", ""], ["Votanti", "500", ""]],
    ]
    out = parse_affluenza(tabelle)
    assert out["elettori"] == 0
    assert out["affluenza_pct"] is None


def test_parse_schede_cella_non_numerica():
    # "N.D." nelle schede -> None senza crash
    tabelle = [
        [["Schede"], ["Bianche", "N.D."],
         ["Non valide (bianche incl.)", "N.D."]],
    ]
    out = parse_schede(tabelle)
    assert out["bianche"] is None
    assert out["non_valide"] is None


# Referendum 12/06/2022 (comune AFFILE): formato reale con due quesiti.
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


def test_parse_referendum():
    r = parse_risultati(HTML_REFERENDUM)
    assert r["candidati"] == []
    assert r["turno"] == "1° turno"
    assert len(r["quesiti"]) == 2
    q = r["quesiti"][0]
    assert q["quesito"].startswith("1. Abrogazione")
    assert q["elettori"] == 1217
    assert q["votanti"] == 251
    assert q["affluenza_pct"] == 20.62
    assert q["valide"] == 240
    assert q["bianche"] == 5
    assert q["non_valide"] == 11
    assert q["si"] == {"voti": 150, "pct": 62.50}
    assert q["no"] == {"voti": 90, "pct": 37.50}
    q2 = r["quesiti"][1]
    assert q2["si"] == {"voti": 120, "pct": 50.42}
    assert q2["no"] == {"voti": 118, "pct": 49.58}


def test_parse_referendum_diretto():
    # la funzione dedicata ritorna la stessa struttura usata da parse_risultati
    out = parse_referendum(HTML_REFERENDUM)
    assert len(out["quesiti"]) == 2
    assert out["quesiti"][0]["elettori"] == 1217


def test_rileva_turno_ballottaggio():
    # header con "II turno" -> ballottaggio (case-insensitive)
    assert rileva_turno("<th>Affluenza I turno II turno</th>") == "ballottaggio"
    assert rileva_turno("<th>Schede I turno ii turno</th>") == "ballottaggio"


def test_rileva_turno_primo():
    assert rileva_turno("<th>Affluenza</th>") == "1° turno"
    assert rileva_turno("<th>Candidati e Liste/Gruppi</th>") == "1° turno"


# ---------------------------------------------------------------------------
# Elezioni regionali (Lazio 12/02/2023): candidati presidente (righe
# class='leader') con liste collegate, totali di coalizione e complessivi.
# ---------------------------------------------------------------------------

# Fixture semplificata ma fedele al formato reale: 2 leader + liste,
# 'totale_liste' (Totale coalizione) e 'totalecomplessivovoti' da ignorare.
HTML_REGIONALI = """
<html><body>
<h3>Regionali 12/02/2023 Area ITALIA Regione LAZIO</h3>
<table class="dati_riepilogo" summary='Riepilogo elezione'>
<tr><th colspan='3'>Affluenza</th></tr>
<tr><th>Elettori</th><td class='align_right'>4.791.612</td><td></td></tr>
<tr><th>Votanti</th><td class='align_right'>1.782.656</td><td class='percentuale'>37,20 %</td></tr>
</table>
<table class="dati_riepilogo" summary='Riepilogo elezione'>
<tr><th colspan='2'>Schede</th></tr>
<tr><th>Bianche</th><td class='align_right'>10.594</td></tr>
<tr><th>Non valide (bianche incl.)</th><td class='align_right'>45.111</td></tr>
</table>
<table class="dati table-striped" summary='Risultato elezione'>
<thead><tr class='riga_testata'>
<th colspan='3' class='align_left' id='hcandidato'>Candidati / Liste regionali e Liste circoscrizionali</th>
<th class='align_right'></th><th class='align_center'></th>
<th class='align_right' id='hvoti'>Voti</th>
<th class='align_center' id='hpercentuale'>%</th>
<th class='align_right' id='hseggi'>Seggi</th>
</tr></thead>
<tbody>
<tr class='leader'>
<td class='simbolo_leader'><img src="x.png" title="FRANCESCO ROCCA" alt="FRANCESCO ROCCA"/></td>
<td headers='hcandidato' id="candidato0" scope='row'>ROCCA FRANCESCO <br /><span class='listino'>FRANCESCO ROCCA</span></td>
<td class='text-left'>Eletto pres.</td><td class='align_right'></td><td class='align_center'></td>
<td class='align_right vertical_align'>936.388</td><td class='percentuale vertical_percentuale'>53,89</td><td></td>
</tr>
<tr>
<td class='simbolo_lista'></td><th class='candidato' id='lista0_0'>FRATELLI D'ITALIA</th>
<td class='apparentamento'></td><td></td><td></td>
<td class='align_right vertical_align'>520.731</td><td class='percentuale vertical_percentuale'>33,63</td><td class='align_right vertical_align'>22</td>
</tr>
<tr>
<td class='simbolo_lista'></td><th class='candidato' id='lista0_1'>LEGA</th>
<td class='apparentamento'></td><td></td><td></td>
<td class='align_right vertical_align'>131.811</td><td class='percentuale vertical_percentuale'>8,51</td><td class='align_right vertical_align'>3</td>
</tr>
<tr class='totale_liste'>
<td></td><td id='htotalecoalizione0'>Totale coalizione</td><td></td><td></td><td></td>
<td class='align_right vertical_align'>856.966</td><td class='percentuale vertical_percentuale'>55,35</td><td class='align_right vertical_align'>30</td>
</tr>
<tr class='leader'>
<td class='simbolo_leader'><img src="x.png" title="ALESSIO D'AMATO" alt="ALESSIO D'AMATO"/></td>
<td headers='hcandidato' id="candidato1" scope='row'>D'AMATO ALESSIO <br /><span class='listino'>ALESSIO D'AMATO</span></td>
<td class='text-left'>Eletto cons.</td><td class='align_right'></td><td class='align_center'></td>
<td class='align_right vertical_align'>581.974</td><td class='percentuale vertical_percentuale'>33,49</td><td></td>
</tr>
<tr>
<td class='simbolo_lista'></td><th class='candidato' id='lista1_0'>PARTITO DEMOCRATICO</th>
<td class='apparentamento'></td><td></td><td></td>
<td class='align_right vertical_align'>313.658</td><td class='percentuale vertical_percentuale'>20,26</td><td class='align_right vertical_align'>10</td>
</tr>
<tr class='totale_liste'>
<td></td><td id='htotalecoalizione1'>Totale coalizione</td><td></td><td></td><td></td>
<td class='align_right vertical_align'>519.761</td><td class='percentuale vertical_percentuale'>33,57</td><td class='align_right vertical_align'>14</td>
</tr>
<tr class='totalecomplessivovoti'>
<td class='align_left' id='htotalecomplessivovoti'>TOTALE</td>
<td id='htotale'>CANDIDATI | LISTE REGIONALI</td><td></td><td></td>
<td class='align_right vertical_align'>1.737.545</td><td></td><td></td>
</tr>
<tr class='totalecomplessivovoti'>
<td id='htotale'>LISTE CIRCOSCRIZIONALI</td><td></td><td></td>
<td class='align_right vertical_align'>1.548.288</td><td></td>
<td class='align_right vertical_align'>49</td>
</tr>
</tbody>
</table>
</body></html>
"""


def test_parse_regionali():
    r = parse_risultati(HTML_REGIONALI)
    assert r["elettori"] == 4791612
    assert r["votanti"] == 1782656
    assert r["affluenza_pct"] == 37.20
    assert r["bianche"] == 10594
    assert r["non_valide"] == 45111
    assert len(r["candidati"]) == 2
    rocca, damato = r["candidati"]
    # nome presidente dal <span class='listino'> (NOME COGNOME)
    assert rocca["candidato"] == "FRANCESCO ROCCA"
    assert rocca["eletto"] is True
    assert rocca["voti_candidato"] == 936388
    assert rocca["pct_candidato"] == 53.89
    assert [lst["lista"] for lst in rocca["liste"]] == ["FRATELLI D'ITALIA", "LEGA"]
    assert rocca["liste"][0]["voti"] == 520731
    assert rocca["liste"][0]["pct"] == 33.63
    assert rocca["liste"][0]["seggi"] == 22
    assert damato["candidato"] == "ALESSIO D'AMATO"
    assert damato["eletto"] is True
    assert damato["voti_candidato"] == 581974
    assert damato["liste"][0]["lista"] == "PARTITO DEMOCRATICO"
    assert damato["liste"][0]["seggi"] == 10
    # nessun candidato fittizio ricavato dalle righe di totale
    nomi = [c["candidato"] for c in r["candidati"]]
    assert "LISTE CIRCOSCRIZIONALI" not in nomi
    assert "Totale coalizione" not in nomi


def test_parse_candidati_regionali_diretto():
    cand = parse_candidati_regionali(HTML_REGIONALI)
    assert len(cand) == 2
    assert cand[0]["candidato"] == "FRANCESCO ROCCA"
    assert cand[1]["candidato"] == "ALESSIO D'AMATO"


FIXTURE_REGIONALI = Path(__file__).parent / "fixtures" / "regionali_2023_lazio.html"


@pytest.mark.skipif(not FIXTURE_REGIONALI.exists(),
                    reason="fixture reale regionali assente")
def test_parse_regionali_fixture_reale():
    html = FIXTURE_REGIONALI.read_text(encoding="utf-8")
    r = parse_risultati(html)
    assert len(r["candidati"]) == 5
    nomi = [c["candidato"] for c in r["candidati"]]
    assert nomi == ["FRANCESCO ROCCA", "ALESSIO D'AMATO", "DONATELLA BIANCHI",
                    "SONIA PECORILLI", "ROSA RINALDI"]
    assert "LISTE CIRCOSCRIZIONALI" not in nomi
    rocca = r["candidati"][0]
    assert rocca["eletto"] is True
    assert rocca["voti_candidato"] == 936388
    assert rocca["pct_candidato"] == 53.89
    assert rocca["liste"][0]["lista"] == "FRATELLI D'ITALIA"
    assert rocca["liste"][0]["seggi"] == 22
    assert len(rocca["liste"]) == 6
    damato = r["candidati"][1]
    assert damato["eletto"] is True
    assert damato["voti_candidato"] == 581974
    rinaldi = r["candidati"][4]
    assert rinaldi["eletto"] is False
    assert rinaldi["voti_candidato"] == 15361
    assert rinaldi["pct_candidato"] == 0.88
