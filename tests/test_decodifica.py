"""Test della decodifica delle opzioni del form (replica del JS del sito)."""

import pytest

from estrattore_elezioni import decodifica_area, decodifica_opzione


def test_decodifica_opzione_regione():
    assert decodifica_opzione("18-lev118") == ("18", "lev1", "18")


def test_decodifica_opzione_provincia():
    assert decodifica_opzione("97-lev297") == ("97", "lev2", "97")


def test_decodifica_opzione_comune():
    # il valore dopo "lev3" è il suffisso (230), non "3230"
    assert decodifica_opzione("970230-lev3230") == ("970230", "lev3", "230")


def test_decodifica_opzione_roma():
    assert decodifica_opzione("58091-lev558091") == ("58091", "lev5", "58091")


def test_decodifica_area():
    assert decodifica_area("I-lev00-levsut00-msN-tpeA") == (
        "&tpa=I&lev0=0&levsut0=0&ms=N&tpe=A"
    )


def test_decodifica_area_valle_aosta():
    assert decodifica_area("H-lev027-levsut01-msN-tpeI") == (
        "&tpa=H&lev0=27&levsut0=1&ms=N&tpe=I"
    )


def test_decodifica_valori_malformati_non_crash():
    # la decodifica non deve mai sollevare eccezioni su input inattesi:
    # al massimo produce valori vuoti (il sito reale usa sempre il formato
    # valido, ma la robustezza protegge da pagine anomale)
    for valore in ["", "18", "18-", "-lev118", "a-b-c-d-e"]:
        out = decodifica_opzione(valore)
        assert isinstance(out, tuple) and len(out) == 3
