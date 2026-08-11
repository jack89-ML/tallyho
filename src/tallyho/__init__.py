"""TallyHo — serie storica elettorale italiana dall'Archivio Storico DAIT."""

__version__ = "1.0.0"

from .tallyho import (  # noqa: F401
    BASE,
    decodifica_area,
    decodifica_opzione,
    estrai_lista,
    estrai_tabelle,
    integra_dait,
    leggi_date,
    leggi_onchange,
    leggi_select,
    pagina_ha_risultati,
    parse_affluenza,
    parse_candidati,
    parse_risultati,
    parse_schede,
    scendi_livello,
    trova_comune,
)

__all__ = [
    "BASE",
    "decodifica_area",
    "decodifica_opzione",
    "estrai_lista",
    "estrai_tabelle",
    "integra_dait",
    "leggi_date",
    "leggi_onchange",
    "leggi_select",
    "pagina_ha_risultati",
    "parse_affluenza",
    "parse_candidati",
    "parse_risultati",
    "parse_schede",
    "scendi_livello",
    "trova_comune",
]
