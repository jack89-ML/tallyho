"""TallyHo — serie storica elettorale italiana dall'Archivio Storico DAIT."""

__version__ = "1.0.0"

from .costanti import BASE  # noqa: F401
from .export import integra_dait  # noqa: F401
from .navigazione import (  # noqa: F401
    decodifica_area,
    decodifica_opzione,
    leggi_date,
    leggi_onchange,
    leggi_select,
    pagina_ha_risultati,
    scendi_livello,
    trova_comune,
)
from .parsing import (  # noqa: F401
    estrai_lista,
    estrai_tabelle,
    parse_affluenza,
    parse_candidati,
    parse_referendum,
    parse_risultati,
    parse_schede,
    rileva_turno,
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
    "parse_referendum",
    "parse_risultati",
    "parse_schede",
    "rileva_turno",
    "scendi_livello",
    "trova_comune",
]
