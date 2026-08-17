"""Test della mappa dei tipi di elezione (costanti condivise)."""

from tallyho.costanti import TIPO_ETICHETTE


def test_tipo_etichette_completa():
    # tutti i codici tpel supportati dalla CLI hanno un'etichetta leggibile
    attesi = {
        "G": "Comunali",
        "R": "Regionali",
        "P": "Provinciali",
        "C": "Camera",
        "S": "Senato",
        "E": "Europee",
        "F": "Referendum",
        "A": "Costituente",
    }
    assert TIPO_ETICHETTE == attesi


def test_tipo_etichette_get_fallback():
    # codice ignoto -> ritorna il codice stesso (mai stringa vuota/None)
    assert TIPO_ETICHETTE.get("G", "G") == "Comunali"
    assert TIPO_ETICHETTE.get("X", "X") == "X"
