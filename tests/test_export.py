"""Test dell'export CSV/JSON da un dizionario di risultati fittizio."""

import json

from tallyho.export import esporta_csv, esporta_json

RISULTATI = {
    "ROMA": [
        {
            "data_elezione": "03/10/2021",
            "comune": "ROMA",
            "provincia": "ROMA",
            "turno": "ballottaggio",
            "elettori": 2359248,
            "votanti": 1145268,
            "affluenza_pct": 48.54,
            "bianche": 12389,
            "non_valide": 35356,
            "candidati": [
                {
                    "candidato": "GUALTIERI ROBERTO",
                    "eletto": True,
                    "voti_candidato": 299976,
                    "pct_candidato": 27.03,
                    "liste": [
                        {"lista": "PARTITO DEMOCRATICO", "voti": 166194,
                         "pct": 16.38, "seggi": 18},
                    ],
                },
                {
                    "candidato": "MICHELLI ENRICO",
                    "eletto": False,
                    "voti_candidato": 299594,
                    "pct_candidato": 26.99,
                    "liste": [],
                },
            ],
        },
    ],
}


def test_esporta_csv(tmp_path):
    percorso = tmp_path / "elezioni.csv"
    esporta_csv(str(percorso), ["ROMA"], RISULTATI)
    raw = percorso.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM UTF-8 per Excel
    testo = percorso.read_text(encoding="utf-8-sig")
    righe = testo.splitlines()
    header = righe[0].split(";")
    assert header[0] == "data_elezione"
    assert header[-1] == "seggi"
    assert len(header) == 17
    assert header[3] == "turno"
    # una riga per ogni lista + una riga per il candidato senza lista
    assert len(righe) == 3
    assert "PARTITO DEMOCRATICO" in testo
    assert "PARTITO DEMOCRATICO;166194;16.38;18" in testo  # lista + voti/%/seggi
    # il candidato senza liste finisce con 4 campi vuoti
    assert "MICHELLI ENRICO;False;299594;26.99;;;;" in testo
    # il campo turno (ballottaggio) è valorizzato nella prima riga
    assert "ROMA;ROMA;ballottaggio;2359248" in testo


def test_esporta_json(tmp_path):
    percorso = tmp_path / "elezioni.json"
    amministratori = {
        "ROMA": [{"carica": "Sindaco", "nominativo": "MARIO ROSSI",
                  "data_elezione": "03/10/2021", "data_entrata_in_carica": "18/10/2021",
                  "lista": "PARTITO DEMOCRATICO"}],
    }
    esporta_json(str(percorso), ["ROMA"], RISULTATI,
                 [{"data_elezione": "03/10/2021", "comune": "ROMA", "esito": "OK"}],
                 amministratori_dait=amministratori, generato="20260101_120000")
    payload = json.loads(percorso.read_text(encoding="utf-8"))
    assert set(payload) == {"generato", "comuni", "risultati", "log",
                            "amministratori_dait"}
    assert payload["generato"] == "20260101_120000"
    assert payload["comuni"] == ["ROMA"]
    assert payload["log"][0]["esito"] == "OK"
    lista = payload["risultati"]["ROMA"][0]["candidati"][0]["liste"][0]
    assert lista["lista"] == "PARTITO DEMOCRATICO"
    assert payload["risultati"]["ROMA"][0]["turno"] == "ballottaggio"
    assert payload["amministratori_dait"]["ROMA"][0]["carica"] == "Sindaco"


def test_esporta_json_senza_dait(tmp_path):
    percorso = tmp_path / "elezioni2.json"
    esporta_json(str(percorso), ["ROMA"], RISULTATI, [], generato="20260101_120000")
    payload = json.loads(percorso.read_text(encoding="utf-8"))
    assert "amministratori_dait" not in payload
