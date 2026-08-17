"""Test del caricamento (TOML/YAML) e dell'applicazione del file di config."""

import sys
import types

import pytest


def _toml_disponibile():
    try:
        import tomllib  # noqa: F401
        return True
    except ImportError:
        try:
            import tomli  # noqa: F401
            return True
        except ImportError:
            return False


from tallyho.tallyho import _applica_config, _carica_config, _imposta_default


@pytest.mark.skipif(not _toml_disponibile(), reason="tomllib/tomli non disponibili")
def test_carica_config_toml(tmp_path):
    p = tmp_path / "tallyho.toml"
    p.write_text('comuni = "ROMA,MILANO"\ntipo = "G"\nout = "dati"\n'
                 "sleep = 1.5\n", encoding="utf-8")
    cfg = _carica_config(str(p))
    assert cfg == {"comuni": "ROMA,MILANO", "tipo": "G", "out": "dati",
                   "sleep": 1.5}


def test_carica_config_yaml(tmp_path):
    pytest.importorskip("yaml")
    p = tmp_path / "tallyho.yaml"
    p.write_text("comuni: ROMA\nsleep: 2.0\n", encoding="utf-8")
    cfg = _carica_config(str(p))
    assert cfg == {"comuni": "ROMA", "sleep": 2.0}


def test_carica_config_inesistente(tmp_path):
    assert _carica_config(str(tmp_path / "non_esiste.toml")) == {}


def test_carica_config_estensione_non_supportata(tmp_path):
    p = tmp_path / "cfg.ini"
    p.write_text("[sezione]\nchiave = 1\n", encoding="utf-8")
    assert _carica_config(str(p)) == {}


@pytest.mark.skipif(not _toml_disponibile(), reason="tomllib/tomli non disponibili")
def test_carica_config_toml_non_valido(tmp_path):
    p = tmp_path / "rotto.toml"
    p.write_text("comuni = [non chiuso\n", encoding="utf-8")
    assert _carica_config(str(p)) == {}


def test_applica_config_sovrascrive_i_default():
    # simula args dopo parse_args() con SUPPRESS: nessun attributo presente
    args = types.SimpleNamespace()
    _applica_config(args, {"comuni": "ROMA", "sleep": 2.0, "out": "dati",
                           "tipo": "R", "long": True})
    _imposta_default(args)
    assert args.comuni == "ROMA"
    assert args.sleep == 2.0
    assert args.out == "dati"
    assert args.tipo == "R"
    assert args.long is True
    # opzioni non toccate dal config: restano al default reale
    assert args.province == "ROMA"
    assert args.nome_regione == "LAZIO"
    assert args.xlsx is False
    assert args.parquet is False


def test_applica_config_precedenza_cli():
    # la CLI ha già impostato comuni/sleep -> il config NON li sovrascrive
    args = types.SimpleNamespace(comuni="MILANO", sleep=3.0)
    _applica_config(args, {"comuni": "ROMA", "sleep": 1.0, "out": "dati"})
    _imposta_default(args)
    assert args.comuni == "MILANO"
    assert args.sleep == 3.0
    assert args.out == "dati"  # out non era in CLI -> arriva dal config


def test_applica_config_trattino_come_underscore():
    args = types.SimpleNamespace()
    _applica_config(args, {"nome-regione": "TOSCANA", "solo-ultima-data": True})
    _imposta_default(args)
    assert args.nome_regione == "TOSCANA"
    assert args.solo_ultima_data is True


def test_applica_config_lista_comuni_e_province():
    args = types.SimpleNamespace()
    _applica_config(args, {"comuni": ["ROMA", "MILANO"],
                           "province": ["ROMA", "COMO"]})
    _imposta_default(args)
    assert args.comuni == "ROMA,MILANO"
    assert args.province == "ROMA,COMO"


def test_applica_config_chiave_sconosciuta_ignorata():
    args = types.SimpleNamespace()
    _applica_config(args, {"boh": 1, "comuni": "ROMA"})
    _imposta_default(args)
    assert not hasattr(args, "boh")
    assert args.comuni == "ROMA"


def test_esporta_xlsx_senza_openpyxl(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "openpyxl", None)
    from tallyho.export import esporta_xlsx
    percorso = tmp_path / "elezioni.xlsx"
    esporta_xlsx(str(percorso), ["ROMA"], {})  # non deve sollevare
    assert not percorso.exists()


def test_esporta_parquet_senza_pyarrow(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    from tallyho.export import esporta_parquet
    percorso = tmp_path / "elezioni.parquet"
    esporta_parquet(str(percorso), ["ROMA"], {})  # non deve sollevare
    assert not percorso.exists()


@pytest.mark.skipif(not _toml_disponibile(), reason="tomllib/tomli non disponibili")
def test_main_applica_config_end_to_end(tmp_path, monkeypatch):
    """End-to-end offline: il config TOML viene applicato davvero (comuni,
    out e sleep), attraverso il vero parser e `main()`."""
    import tallyho.tallyho as th

    cfg = tmp_path / "tallyho.toml"
    out_dir = tmp_path / "output_qui"
    cfg.write_text(f'comuni = "ROMA"\nout = "{out_dir}"\nsleep = 0.05\n',
                   encoding="utf-8")

    sleep_chiamate = []
    monkeypatch.setattr(th.time, "sleep",
                        lambda s: sleep_chiamate.append(s))

    # stub della sessione HTTP: nessuna rete
    class _FakeResp:
        text = ""

        def raise_for_status(self):
            return None

    class _FakeSession:
        def __init__(self, ttl=0):
            self.headers = {}
            self.ttl = ttl

        def get(self, url, timeout=30):
            return _FakeResp()

    monkeypatch.setattr(th, "CachedSession", _FakeSession)
    monkeypatch.setattr(th, "leggi_date", lambda html: ["01/01/2020"])
    monkeypatch.setattr(th, "trova_comune", lambda *a, **k: (None, None))

    monkeypatch.setattr(sys, "argv", ["tallyho", "--config", str(cfg)])
    th.main()

    out_dir = tmp_path / "output_qui"
    assert out_dir.is_dir(), "il config 'out' non è stato applicato"
    csv_files = list(out_dir.glob("*.csv"))
    assert len(csv_files) == 1, "il config 'comuni' non ha fatto scrivere il CSV"
    # sleep dal config (0.05) è stato davvero usato, non il default 1.2
    assert sleep_chiamate and all(s == 0.05 for s in sleep_chiamate)
