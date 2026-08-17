"""Test di integra_dait con un mini-CSV in memoria (nessuna rete)."""

from tallyho import integra_dait

# Replica del formato reale di ammcom.csv: 2 righe di titolo/aggiornamento,
# poi l'intestazione con i nomi dei campi, poi le righe dati (tutti i campi
# quotati, delimitatore ';').
CSV_DAIT = """\
"ANAGRAFE DEGLI AMMINISTRATORI LOCALI"
"Aggiornato al: 01/01/2026"
"denominazione_comune";"nome";"cognome";"descrizione_carica";"data_elezione";"data_entrata_in_carica";"lista_appartenenza/collegamento"
"ROMA";"MARIO";"ROSSI";"Sindaco";"03/10/2021";"18/10/2021";"PARTITO DEMOCRATICO"
"ROMA";"LUCA";"BIANCHI";"Assessore";"03/10/2021";"18/10/2021";"PARTITO DEMOCRATICO"
"MILANO";"GIUSEPPE";"VERDI";"Sindaco";"03/10/2021";"18/10/2021";"LEGA"
"""


def test_integra_dait_filtra_per_comune(tmp_path):
    p = tmp_path / "ammcom.csv"
    p.write_text(CSV_DAIT, encoding="utf-8")
    out = integra_dait(str(p), ["ROMA"])
    # solo il comune richiesto, non MILANO
    assert set(out) == {"ROMA"}
    assert len(out["ROMA"]) == 2
    sindaco = [r for r in out["ROMA"] if r["carica"] == "Sindaco"][0]
    assert sindaco["nominativo"] == "MARIO ROSSI"
    assert sindaco["lista"] == "PARTITO DEMOCRATICO"
    assert sindaco["data_elezione"] == "03/10/2021"
    assert sindaco["data_entrata_in_carica"] == "18/10/2021"


def test_integra_dait_file_mancante():
    assert integra_dait("/non/esiste/ammcom.csv", ["ROMA"]) == {}
