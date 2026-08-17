"""Test dell'export CSV/JSON da un dizionario di risultati fittizio."""

import json
import sys
import types

from tallyho.export import (esporta_csv, esporta_json, esporta_long,
                            esporta_parquet, esporta_xlsx)

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


def test_esporta_long(tmp_path):
    percorso = tmp_path / "elezioni_long.csv"
    esporta_long(str(percorso), ["ROMA"], RISULTATI)
    raw = percorso.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM UTF-8
    righe = percorso.read_text(encoding="utf-8-sig").splitlines()
    header = righe[0].split(";")
    assert header[:6] == ["data_elezione", "tipo", "turno", "comune",
                          "provincia", "ambito"]
    assert header[-1] == "seggi"
    # 4 righe scheda (elettori/votanti/bianche/non_valide) + 1 candidato
    # con lista + 1 candidato senza lista = 7 righe di dati
    assert len(righe) == 8
    # righe di livello scheda
    assert "scheda;elettori;2359248;;;" in righe[1]
    assert "scheda;votanti;1145268;48.54;;" in righe[2]
    # riga candidato con lista
    assert "candidato;GUALTIERI ROBERTO;299976;27.03;True;" in righe[5]
    # riga lista
    assert "lista;PARTITO DEMOCRATICO;166194;16.38;;18" in righe[6]
    # candidato senza lista (seggi vuoto)
    assert "candidato;MICHELLI ENRICO;299594;26.99;False;" in righe[7]


def test_esporta_long_senza_record(tmp_path):
    percorso = tmp_path / "elezioni_long_vuoto.csv"
    esporta_long(str(percorso), ["ROMA"], {"ROMA": []})
    righe = percorso.read_text(encoding="utf-8-sig").splitlines()
    # solo l'intestazione, nessuna riga di dati
    assert len(righe) == 1
    assert righe[0].split(";")[0] == "data_elezione"


REFERENDUM = {
    "AFFILE": [
        {
            "data_elezione": "12/06/2022",
            "comune": "AFFILE",
            "provincia": "ROMA",
            "turno": "1° turno",
            "elettori": None, "votanti": None, "affluenza_pct": None,
            "bianche": None, "non_valide": None,
            "candidati": [],
            "quesiti": [
                {"quesito": "Q1. Test", "elettori": 1217, "votanti": 251,
                 "affluenza_pct": 20.62, "valide": 240, "bianche": 5,
                 "non_valide": 11,
                 "si": {"voti": 150, "pct": 62.5},
                 "no": {"voti": 90, "pct": 37.5}},
            ],
        },
    ],
}


def test_esporta_csv_con_referendum(tmp_path):
    percorso = tmp_path / "elezioni_ref.csv"
    esporta_csv(str(percorso), ["AFFILE"], REFERENDUM)
    testo = percorso.read_text(encoding="utf-8-sig")
    righe = testo.splitlines()
    # header + 2 righe (SI e NO del quesito)
    assert len(righe) == 3
    assert "12/06/2022;AFFILE;ROMA;1° turno;1217;251;20.62;5;11;Q1. Test;;150;62.5;SI;150;62.5;" in testo
    assert "12/06/2022;AFFILE;ROMA;1° turno;1217;251;20.62;5;11;Q1. Test;;90;37.5;NO;90;37.5;" in testo


def test_esporta_long_con_referendum(tmp_path):
    percorso = tmp_path / "elezioni_long_ref.csv"
    esporta_long(str(percorso), ["AFFILE"], REFERENDUM)
    testo = percorso.read_text(encoding="utf-8-sig")
    righe = testo.splitlines()
    # header + 4 righe scheda record (None) + 4 scheda quesito + 2 quesito = 11
    assert len(righe) == 11
    assert "scheda;elettori;1217;;;" in testo
    assert "scheda;votanti;251;20.62;;" in testo
    assert "quesito;Q1. Test (SI);150;62.5;;" in testo
    assert "quesito;Q1. Test (NO);90;37.5;;" in testo


# --------------------------------------------------------------------------
# Test positivi xlsx/parquet (moduli finti openpyxl/pyarrow, non installati)
# --------------------------------------------------------------------------

class _FakeWorksheet:
    def __init__(self):
        self.title = "risultati"
        self.righe = []

    def append(self, riga):
        self.righe.append(riga)


class _FakeWorkbook:
    def __init__(self):
        self.active = _FakeWorksheet()

    def save(self, percorso):
        with open(percorso, "w", encoding="utf-8") as f:
            for riga in self.active.righe:
                f.write(";".join("" if x is None else str(x) for x in riga))
                f.write("\n")


def _modulo_openpyxl_finto():
    m = types.ModuleType("openpyxl")
    m.Workbook = _FakeWorkbook
    return m


class _FakeTable:
    def __init__(self, data):
        self.data = data


def _modulo_pyarrow_finto():
    m = types.ModuleType("pyarrow")

    def table(data):
        return _FakeTable(data)

    def array(lst, tipo=None):
        return list(lst)

    def string():
        return "string"

    m.table = table
    m.array = array
    m.string = string
    return m


def _modulo_parquet_finto():
    m = types.ModuleType("pyarrow.parquet")

    def write_table(tabella, percorso):
        colonne = list(tabella.data.keys())
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(";".join(colonne) + "\n")
            n = len(tabella.data[colonne[0]]) if colonne else 0
            for i in range(n):
                f.write(";".join("" if tabella.data[c][i] is None
                                 else str(tabella.data[c][i])
                                 for c in colonne) + "\n")

    m.write_table = write_table
    return m


def test_esporta_xlsx_con_referendum(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "openpyxl", _modulo_openpyxl_finto())
    percorso = tmp_path / "elezioni_ref.xlsx"
    esporta_xlsx(str(percorso), ["AFFILE"], REFERENDUM)
    assert percorso.exists()
    testo = percorso.read_text(encoding="utf-8")
    assert "Q1. Test" in testo
    assert "SI" in testo
    assert "NO" in testo


def test_esporta_parquet_con_referendum(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pyarrow", _modulo_pyarrow_finto())
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", _modulo_parquet_finto())
    percorso = tmp_path / "elezioni_ref.parquet"
    esporta_parquet(str(percorso), ["AFFILE"], REFERENDUM)
    assert percorso.exists()
    testo = percorso.read_text(encoding="utf-8")
    assert "Q1. Test" in testo
    assert "SI" in testo
    assert "NO" in testo
