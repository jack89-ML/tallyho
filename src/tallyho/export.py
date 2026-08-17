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
                        for lista in c["liste"]:
                            w.writerow(riga + [lista["lista"], lista["voti"],
                                               lista["pct"], lista["seggi"]])
                    else:
                        w.writerow(riga + ["", "", "", ""])
                # referendum: una riga per quesito, due righe SI/NO
                for q in rec.get("quesiti", []):
                    q_base = [rec["data_elezione"], rec["comune"],
                              rec["provincia"], rec.get("turno", "1° turno"),
                              q["elettori"], q["votanti"],
                              q["affluenza_pct"], q["bianche"],
                              q["non_valide"]]
                    titolo = q["quesito"]
                    w.writerow(q_base + [titolo, "", q["si"]["voti"],
                                         q["si"]["pct"], "SI",
                                         q["si"]["voti"], q["si"]["pct"], ""])
                    w.writerow(q_base + [titolo, "", q["no"]["voti"],
                                         q["no"]["pct"], "NO",
                                         q["no"]["voti"], q["no"]["pct"], ""])


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


def esporta_long(percorso: str, comuni: list, risultati: dict) -> None:
    """Scrive i risultati in formato LONG/TIDY normalizzato (una riga per
    osservazione), pronto per pandas/R senza post-processing.

    Colonne: data_elezione, tipo, turno, comune, provincia, ambito
    (scheda|candidato|lista), nome, voti, pct, eletto, seggi.
    La riga di livello 'scheda' porta elettori/votanti/affluenza (in voti/pct).
    """
    with open(percorso, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data_elezione", "tipo", "turno", "comune", "provincia",
                    "ambito", "nome", "voti", "pct", "eletto", "seggi"])
        for comune in comuni:
            for rec in risultati[comune]:
                base = [rec["data_elezione"], rec.get("tipo", ""),
                        rec.get("turno", "1° turno"), rec["comune"],
                        rec["provincia"]]
                # riga riepilogo schede (elettori/votanti/affluenza)
                w.writerow(base + ["scheda", "elettori", rec["elettori"],
                                   "", "", ""])
                w.writerow(base + ["scheda", "votanti", rec["votanti"],
                                   rec["affluenza_pct"], "", ""])
                w.writerow(base + ["scheda", "bianche", rec["bianche"],
                                   "", "", ""])
                w.writerow(base + ["scheda", "non_valide",
                                   rec["non_valide"], "", "", ""])
                for c in rec["candidati"]:
                    w.writerow(base + ["candidato", c["candidato"] or "",
                                       c["voti_candidato"],
                                       c["pct_candidato"], c["eletto"], ""])
                    for lista in c["liste"]:
                        w.writerow(base + ["lista", lista["lista"], lista["voti"],
                                           lista["pct"], "", lista["seggi"]])
                # referendum: righe scheda + due righe per quesito (SI/NO)
                for q in rec.get("quesiti", []):
                    titolo = q["quesito"]
                    w.writerow(base + ["scheda", "elettori", q["elettori"],
                                       "", "", ""])
                    w.writerow(base + ["scheda", "votanti", q["votanti"],
                                       q["affluenza_pct"], "", ""])
                    w.writerow(base + ["scheda", "bianche", q["bianche"],
                                       "", "", ""])
                    w.writerow(base + ["scheda", "non_valide",
                                       q["non_valide"], "", "", ""])
                    w.writerow(base + ["quesito", titolo + " (SI)",
                                       q["si"]["voti"], q["si"]["pct"],
                                       "", ""])
                    w.writerow(base + ["quesito", titolo + " (NO)",
                                       q["no"]["voti"], q["no"]["pct"],
                                       "", ""])


def esporta_xlsx(percorso: str, comuni: list, risultati: dict) -> None:
    """Scrive i risultati in Excel (.xlsx) — richiede il pacchetto opzionale
    openpyxl (pip install tallyho[xlsx]). Struttura: un foglio 'risultati'
    con le stesse righe del CSV (una riga per lista/candidato).
    """
    try:
        import openpyxl
    except ImportError:
        print("[!] Export Excel richiede openpyxl: "
              "pip install 'tallyho[xlsx]'")
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "risultati"
    header = ["data_elezione", "comune", "provincia", "turno", "elettori",
              "votanti", "affluenza_pct", "bianche", "non_valide",
              "candidato", "eletto", "voti_candidato", "pct_candidato",
              "lista", "voti_lista", "pct_lista", "seggi"]
    ws.append(header)
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
                    for lista in c["liste"]:
                        ws.append(riga + [lista["lista"], lista["voti"], lista["pct"],
                                          lista["seggi"]])
                else:
                    ws.append(riga + ["", "", "", ""])
            for q in rec.get("quesiti", []):
                q_base = [rec["data_elezione"], rec["comune"],
                          rec["provincia"], rec.get("turno", "1° turno"),
                          q["elettori"], q["votanti"], q["affluenza_pct"],
                          q["bianche"], q["non_valide"]]
                titolo = q["quesito"]
                ws.append(q_base + [titolo, "", q["si"]["voti"],
                                    q["si"]["pct"], "SI",
                                    q["si"]["voti"], q["si"]["pct"], ""])
                ws.append(q_base + [titolo, "", q["no"]["voti"],
                                    q["no"]["pct"], "NO",
                                    q["no"]["voti"], q["no"]["pct"], ""])
    wb.save(percorso)


def esporta_parquet(percorso: str, comuni: list, risultati: dict) -> None:
    """Scrive i risultati in Parquet — richiede pyarrow
    (pip install tallyho[parquet]). Stessa struttura del CSV.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("[!] Export Parquet richiede pyarrow: "
              "pip install 'tallyho[parquet]'")
        return
    righe = []
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
                    for lista in c["liste"]:
                        righe.append(riga + [lista["lista"], lista["voti"], lista["pct"],
                                             lista["seggi"]])
                else:
                    righe.append(riga + ["", "", "", ""])
            for q in rec.get("quesiti", []):
                q_base = [rec["data_elezione"], rec["comune"],
                          rec["provincia"], rec.get("turno", "1° turno"),
                          q["elettori"], q["votanti"], q["affluenza_pct"],
                          q["bianche"], q["non_valide"]]
                titolo = q["quesito"]
                righe.append(q_base + [titolo, "", q["si"]["voti"],
                                       q["si"]["pct"], "SI",
                                       q["si"]["voti"], q["si"]["pct"], ""])
                righe.append(q_base + [titolo, "", q["no"]["voti"],
                                       q["no"]["pct"], "NO",
                                       q["no"]["voti"], q["no"]["pct"], ""])
    tabelle = ["data_elezione", "comune", "provincia", "turno", "elettori",
               "votanti", "affluenza_pct", "bianche", "non_valide",
               "candidato", "eletto", "voti_candidato", "pct_candidato",
               "lista", "voti_lista", "pct_lista", "seggi"]
    if not righe:
        tabella = pa.table({t: pa.array([], pa.string()) for t in tabelle})
    else:
        tabella = pa.table({t: [r[i] for r in righe]
                            for i, t in enumerate(tabelle)})
    pq.write_table(tabella, percorso)


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
    print("[i] Download anagrafe amministratori DAIT (~30 MB) ...")
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
