"""Test della decodifica delle opzioni del form (replica del JS del sito)."""

from tallyho import decodifica_area, decodifica_opzione


def test_decodifica_opzione_regione():
    assert decodifica_opzione("99-lev199") == ("99", "lev1", "99")


def test_decodifica_opzione_provincia():
    assert decodifica_opzione("98-lev298") == ("98", "lev2", "98")


def test_decodifica_opzione_comune():
    # il valore è tutto ciò che segue "lev3" (es. "53012"), non il codice intero
    assert decodifica_opzione("53012-lev353012") == ("53012", "lev3", "53012")


def test_decodifica_opzione_livello5():
    assert decodifica_opzione("12345-lev512345") == ("12345", "lev5", "12345")


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


def test_decodifica_area_valori_malformati():
    # protezione su input malformati: mai eccezioni, ritorna None quando il
    # formato non ha i 5 segmenti attesi
    for valore in ["", "I", "I-lev0", "a-b", "a-b-c", "I-lev00-levsut00"]:
        assert decodifica_area(valore) is None
