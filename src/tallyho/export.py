"""Export CSV/JSON e integrazione open data DAIT (anagrafe amministratori)."""

import csv
import json
import os
from datetime import datetime
from typing import Optional

import requests

from .costanti import DAIT_AMMCOM_URL, UA


def esporta_csv(percorso: str, comuni: list, risultati: dict) -> None:
    """Scrive i risultati in CSV (delimitatore ';', UTF-8 BOM per Excel).

    Una riga per ogni lista/candidato di ogni consultazione.
    """
    with open(percorso, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data_elezione", "comune", "provincia", "turno",
                    "elettori", "votanti", "affluenza_pct", "bianche",
                    "non_valide", "candidato", "eletto", "voti_candidato",
                    "pct_candidato", "lista", "voti_lista", "pct_lista",
                    "seggi"])
        for comune in comuni:
            for rec in risultati[comune]:
                base = [rec["data_elezione"], rec["comune"], rec["provincia"],
                        rec.get("turno", "1° turno"), rec["elettori"],
                        rec["votanti"], rec["affluenza_pct"], rec["bianche"],
                        rec["non_valide"]]
                for c in rec["candidati"]:
                    riga = base + [c["candidato"] or "", c["eletto"],
                                   c["voti_candidato"], c["pct_candidato"]]
                    if c["liste"]:
                        for l in c["liste"]:
                            w.writerow(riga + [l["lista"], l["voti"],
                                               l["pct"], l["seggi"]])
                    else:
                        w.writerow(riga + ["", "", "", ""])


def esporta_json(percorso: str, comuni: list, risultati: dict, log: list,
                 amministratori_dait: Optional[dict] = None,
                 generato: Optional[str] = None) -> None:
    """Scrive i risultati in JSON (struttura annidata + log di navigazione).

    `amministratori_dait` (se diverso da None) aggiunge la sezione omonima;
    `generato` è il timestamp (default: adesso).
    """
    if generato is None:
        generato = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {"generato": generato, "comuni": comuni,
               "risultati": risultati, "log": log}
    if amministratori_dait is not None:
        payload["amministratori_dait"] = amministratori_dait
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def scarica_ammcom() -> str:
    """Scarica (con cache) l'anagrafe amministratori DAIT.

    Il file completo è ~30 MB e viene aggiornato con cadenza periodica dal
    Ministero: la cache evita di riscaricarlo a ogni run. Ritorna il percorso.
    """
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache",
                             "tallyho")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "ammcom.csv")
    if os.path.isfile(path) and os.path.getsize(path) > 10_000_000:
        print(f"[i] Anagrafe DAIT già in cache: {path}")
        return path
    print(f"[i] Download anagrafe amministratori DAIT (~30 MB) ...")
    r = requests.get(DAIT_AMMCOM_URL, headers={"User-Agent": UA}, timeout=180)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    mb = len(r.content) // (1024 * 1024)
    print(f"[+] Anagrafe DAIT scaricata: {path} ({mb} MB)")
    return path


def integra_dait(csv_path: str, comuni: list) -> dict:
    """
    Legge il CSV dell'anagrafe amministratori (open data DAIT, file
    ammcom.csv, eventualmente filtrato per i comuni di interesse) e ritorna
    un dict {COMUNE: [record...]} con gli amministratori in carica.
    Formato originale: prime 2 righe = titolo e data di aggiornamento,
    terza riga = intestazione con i nomi dei campi (es. ammcom.csv del
    portale dait.interno.gov.it/elezioni/open-data).
    """
    if not os.path.isfile(csv_path):
        print(f"[!] File DAIT non trovato: {csv_path}")
        return {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        righe_raw = f.read().splitlines()
    if not righe_raw:
        print("[!] File DAIT vuoto")
        return {}
    # scarta le prime righe finché non trovo l'intestazione con i nomi
    start = 0
    for i, r in enumerate(righe_raw[:5]):
        if "denominazione_comune" in r and "cognome" in r:
            start = i
            break
    if start == 0 and "denominazione_comune" not in righe_raw[0]:
        print("[!] Intestazione DAIT non trovata nel CSV")
        return {}
    reader = csv.DictReader(righe_raw[start:], delimiter=";",
                            quoting=csv.QUOTE_ALL)
    out = {c: [] for c in comuni}
    for r in reader:
        comune = (r.get("denominazione_comune") or "").strip().upper()
        if comune not in out:
            continue
        carica = (r.get("descrizione_carica") or "").strip()
        if not carica:
            continue
        nominativo = f"{(r.get('nome') or '').strip()} " \
                     f"{(r.get('cognome') or '').strip()}".strip()
        out[comune].append({
            "carica": carica,
            "nominativo": nominativo,
            "data_elezione": (r.get("data_elezione") or "").strip(),
            "data_entrata_in_carica": (r.get("data_entrata_in_carica") or "").strip(),
            "lista": (r.get("lista_appartenenza/collegamento") or "").strip(),
        })
    return out
