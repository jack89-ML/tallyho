"""Costanti condivise: URL base, User-Agent, URL dell'open data DAIT e
mappa dei tipi di elezione."""

BASE = "https://elezionistorico.interno.gov.it/index.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DAIT_AMMCOM_URL = "https://dait.interno.gov.it/documenti/ammcom.csv"

# Codice tpel (parametro del form) -> etichetta leggibile per l'export.
TIPO_ETICHETTE = {
    "G": "Comunali",
    "R": "Regionali",
    "P": "Provinciali",
    "C": "Camera",
    "S": "Senato",
    "E": "Europee",
    "F": "Referendum",
    "A": "Costituente",
}
