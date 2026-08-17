#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tallyho.py — TallyHo: ti porta a spasso nella storia elettorale italiana.

Fonte: https://elezionistorico.interno.gov.it (1946-oggi)
Licenza: MIT

Perché esiste: l'Archivio Storico delle Elezioni del Ministero dell'Interno
è un tesoro — 70 anni di voti, sindaci, liste e affluenze — ma per
guardarlo devi cliccare un form JavaScript a più passi, per ogni data, per
ogni comune, a mano. TallyHo fa i clic al posto tuo: gli dici "portami
tutto quello che ha votato questo comune" e lui scende la gerarchia
(data -> area -> regione -> provincia -> comune) per ogni data disponibile,
estrae i risultati e te li consegna in CSV e JSON, pronti per l'analisi.

Il sito usa un form progressivo pilotato da JavaScript. Ogni <select> ha
un onchange del tipo:

    carica_pagina('index.php?tpel=G&dtel=...&tpa=I&tpe=R&...','ne1',value)

dove `value` è una stringa compatta decodificabile nel formato:

    '99-lev199'        ->  ne1=99&lev1=99          (regione)
    '98-lev298'        ->  ne2=98&lev2=98          (provincia)
    '99999-lev399999'  ->  ne3=99999&lev3=99999    (comune)
    'I-lev00-levsut00-msN-tpeA' -> tpa=I&lev0=0&levsut0=0&ms=N&tpe=A

Questo script riproduce la stessa sequenza di chiamate GET mantenendo una
sessione HTTP, scende lungo la gerarchia fino ai comuni richiesti e salva
i risultati in CSV e JSON. Tally-ho!

Uso:
    tallyho --comuni ROMA,MILANO                 # serie storica
    tallyho --comuni ROMA --tipo G               # solo comunali
    tallyho --comuni ROMA --nome-regione LAZIO   # regione per nome
    tallyho --comuni ROMA --out ./dati --sleep 1.5
    tallyho --elenca regioni --data 14/05/2023   # scopri i valori
    tallyho --comuni ROMA --dait auto            # + anagrafe amministratori
"""

import argparse
import csv
import html as html_mod
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

BASE = "https://elezionistorico.interno.gov.it/index.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# --------------------------------------------------------------------------
# Decodifica dei valori delle <option> (replica esatta della funzione JS
# `carica_pagina` del sito: la variabile è lunga 4 caratteri dopo il primo
# trattino, il valore è tutto ciò che segue).
# --------------------------------------------------------------------------

def decodifica_opzione(valore):
    """Decodifica '99999-lev399999' -> ('99999', 'lev3', '99999').

    Formato: <valore1>-<var2><valore2> dove var2 è lungo 4 caratteri
    (lev1, lev2, lev3...). Input senza trattino restituisce la stringa
    intera come primo elemento (robustezza su pagine anomale).
    """
    if "-" not in valore:
        return valore, "", ""
    p1, resto = valore.split("-", 1)
    var2, p2 = resto[:4], resto[4:]
    return p1, var2, p2


def decodifica_area(valore):
    """Decodifica 'I-lev00-levsut00-msN-tpeA' -> stringa query completa.

    Formato: <tpa>-<var><val>-<var><val>-<var><val>-<var><val> con variabili
    di lunghezza fissa (lev0=4, levsut0=7, ms=2, tpe=3).
    """
    parti = valore.split("-")
    tpa = parti[0]
    var2, p2 = parti[1][:4], parti[1][4:]
    var3, p3 = parti[2][:7], parti[2][7:]
    var4, p4 = parti[3][:2], parti[3][2:]
    var5, p5 = parti[4][:3], parti[4][3:]
    return (f"&tpa={tpa}&{var2}={p2}&{var3}={p3}"
            f"&{var4}={p4}&{var5}={p5}")


# --------------------------------------------------------------------------
# Estrazione della struttura della pagina
# --------------------------------------------------------------------------

def leggi_select(html_page, nome):
    """Ritorna la lista di (valore, testo) delle option di un select."""
    m = re.search(r'<select name="' + nome + r'"[^>]*>(.*?)</select>',
                  html_page, re.S)
    if not m:
        return []
    out = []
    for v, a, t in re.findall(r'<option value="([^"]*)"([^>]*)>([^<]*)',
                              m.group(1)):
        t = t.strip()
        if v and t and v != "0":
            out.append((v, t))
    return out


def leggi_onchange(html_page, nome):
    """Ritorna (page_path, page_var) dall'onchange di un select."""
    m = re.search(r'<select name="' + nome + r'"[^>]*?onchange="'
                  r"carica_pagina\('([^']*)','([^']*)',", html_page)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def leggi_date(html_page):
    """Tutte le date disponibili per il tipo di elezione scelto."""
    return [t for _, t in leggi_select(html_page, "sel_date")]


# --------------------------------------------------------------------------
# Navigazione della gerarchia territoriale
# --------------------------------------------------------------------------

def scendi_livello(sessione, page_path, page_var, valore):
    """Aggiunge il livello selezionato alla URL e carica la pagina."""
    if page_var == "tpa":
        qs = decodifica_area(valore)
    else:
        p1, var2, p2 = decodifica_opzione(valore)
        qs = f"&{page_var}={p1}&{var2}={p2}"
    url = BASE + ("?" + page_path if page_path and not page_path.startswith(
        "index.php?") else "?" + page_path) + qs
    url = url.replace("?index.php?", "?")  # normalizzazione
    if not url.startswith("http"):
        url = "https://elezionistorico.interno.gov.it/" + url.lstrip("/")
    r = sessione.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def trova_comune(sessione, data, comune_target, tipo, regione_value,
                 nome_regione, province_target):
    """
    Percorre data -> area -> regione -> [provincia] -> [comune] in modo
    dinamico, adattandosi al tipo di elezione:
      - comunali/regionali: area Italia -> regione (-> provincia -> comune)
      - politiche (C/S): area Italia -> circoscrizione (testo == nome
        regione) -> provincia -> comune
      - regionali: la discesa si ferma alla regione (niente provincia)
    Ritorna (html_risultati, contesto) se l'area ha votato, altrimenti
    (None, None).
    """
    # passo 1: seleziona la data
    url = f"{BASE}?tpel={tipo}&dtel={data}"
    r = sessione.get(url, timeout=30)
    r.raise_for_status()
    html_p = r.text

    # passo 2: area (solitamente l'unica opzione reale)
    aree = leggi_select(html_p, "sel_aree")
    if not aree:
        return None, None
    pp, pv = leggi_onchange(html_p, "sel_aree")
    html_p = scendi_livello(sessione,
                            pp or f"index.php?tpel={tipo}&dtel={data}&es0=S",
                            "tpa", aree[0][0])

    # passo 3: regione / circoscrizione (livello 2)
    regioni = leggi_select(html_p, "sel_sezione2")
    if not regioni:
        return None, None
    scelta_reg = None
    for v, t in regioni:
        if t.upper() == nome_regione.upper() or v == regione_value:
            scelta_reg = (v, t)
            break
    if scelta_reg is None:
        return None, None
    pp, pv = leggi_onchange(html_p, "sel_sezione2")
    html_p = scendi_livello(sessione, pp, pv, scelta_reg[0])
    contesto = {"data": data, "regione": scelta_reg[1], "provincia": "",
                "comune": comune_target}

    # passo 4: livello 3 (provincia per comunali/regionali, collegi
    # plurinominali per le politiche post-2017, ripartizioni NORD/CENTRO/SUD
    # per le regionali). Se la pagina ha GIÀ i risultati (es. regionali),
    # non scendere oltre.
    if pagina_ha_risultati(html_p):
        return html_p, contesto
    province = leggi_select(html_p, "sel_sezione3")
    if province:
        scelte_prov = [(v, t) for v, t in province
                       if t.upper() in province_target]
        if not scelte_prov:
            # gerarchia diversa (es. collegi plurinominali "LAZIO - P01"):
            # prova tutte le opzioni finché il comune compare al livello 4
            scelte_prov = province
        pp_prov, pv_prov = leggi_onchange(html_p, "sel_sezione3")
        for v_prov, t_prov in scelte_prov:
            html_prov = scendi_livello(sessione, pp_prov, pv_prov, v_prov)
            # passo 5: comune (livello 4) — se non c'è, prova la provincia dopo
            comuni = leggi_select(html_prov, "sel_sezione4")
            if comuni:
                scelta_com = None
                for cv, cn in comuni:
                    if cn.upper() == comune_target.upper():
                        scelta_com = (cv, cn)
                        break
                if scelta_com is None:
                    continue  # comune non in questa provincia
                contesto["provincia"] = t_prov
                pp_com, pv_com = leggi_onchange(html_prov, "sel_sezione4")
                html_p = scendi_livello(sessione, pp_com, pv_com, scelta_com[0])
                return html_p, contesto
            # senza livello comune (es. provinciali per provincia)
            contesto["provincia"] = t_prov
            return html_prov, contesto
        return None, None
    return html_p, contesto


# --------------------------------------------------------------------------
# Parse della pagina dei risultati
# --------------------------------------------------------------------------

def pulisci(cella):
    """Testo di una cella, ripulito."""
    t = re.sub(r"<[^>]+>", "", cella)
    t = html_mod.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def estrai_tabelle(html_page):
    """Ritorna la lista delle tabelle con le righe/celle."""
    tabelle = []
    for tm in re.finditer(r"<table[^>]*>(.*?)</table>", html_page, re.S):
        righe = []
        for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", tm.group(1), re.S):
            celle = [pulisci(c) for c in re.findall(
                r"<t[dh][^>]*>(.*?)</t[dh]>", rm.group(1), re.S)]
            if any(celle):
                righe.append(celle)
        if righe:
            tabelle.append(righe)
    return tabelle


def pagina_ha_risultati(html_page):
    """True se la pagina contiene già la tabella risultati (affluenza +
    candidati o liste), tipico del livello più basso della gerarchia."""
    tabelle = estrai_tabelle(html_page)
    if not tabelle:
        return False
    ha_affluenza = any(tab and tab[0]
                       and "affluenza" in tab[0][0].lower() for tab in tabelle)
    if not ha_affluenza:
        return False
    for tab in tabelle:
        if tab and tab[0]:
            h = tab[0][0].lower()
            if "candidati" in h or h.startswith("liste"):
                return True
    return False


def parse_affluenza(tabelle):
    """Elettori, votanti, percentuale dalla tabella di riepilogo."""
    out = {"elettori": None, "votanti": None, "affluenza_pct": None}
    for tab in tabelle:
        if tab and tab[0] and "affluenza" in tab[0][0].lower():
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("elettori"):
                        out["elettori"] = int(riga[1].replace(".", ""))
                    elif k.startswith("votanti"):
                        out["votanti"] = int(riga[1].replace(".", ""))
                        m = re.search(r"([\d,]+)\s*%", riga[2] if len(riga) > 2 else "")
                        if m:
                            out["affluenza_pct"] = float(m.group(1).replace(",", "."))
    return out


def parse_schede(tabelle):
    """Bianche e non valide."""
    out = {"bianche": None, "non_valide": None}
    for tab in tabelle:
        if tab and tab[0] and "schede" in tab[0][0].lower():
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("bianche"):
                        out["bianche"] = int(riga[1].replace(".", ""))
                    elif k.startswith("non valide"):
                        out["non_valide"] = int(riga[1].replace(".", ""))
    return out


def parse_candidati(tabelle):
    """
    Due formati possibili:
    - moderno (1993+): tabella 'Candidati e Liste/Gruppi' con righe alternate
      candidato (colonna 0) e lista (colonna 1);
    - storico (1970-1985): tabella 'Liste/Gruppi' con sole liste
      (il sindaco era eletto dal consiglio comunale).
    Ritorna una lista di dict.
    """
    risultati = []
    for tab in tabelle:
        if not tab or not tab[0]:
            continue
        header = tab[0][0].lower()
        if "candidati" in header:
            corrente = None
            for riga in tab[1:]:
                if not riga:
                    continue
                prima = riga[0]
                if prima.upper() in ("TOTALE", "LISTE"):
                    continue
                if prima:  # riga candidato
                    voti = riga[-3] if len(riga) >= 3 else ""
                    pct = riga[-2] if len(riga) >= 2 else ""
                    corrente = {
                        "candidato": prima,
                        "eletto": any("eletto" in c.lower() for c in riga[:3]),
                        "voti_candidato": (int(voti.replace(".", ""))
                                           if re.fullmatch(r"[\d.]+", voti) else None),
                        "pct_candidato": (float(pct.replace(",", "."))
                                          if re.fullmatch(r"[\d,]+", pct) else None),
                        "liste": [],
                    }
                    risultati.append(corrente)
                elif len(riga) >= 4 and riga[1]:  # riga lista
                    if corrente is None:
                        continue
                    corrente["liste"].append(
                        estrai_lista(riga[1], riga[2:]))
        elif header.startswith("liste"):  # formato storico
            for riga in tab[1:]:
                if not riga or not any(riga):
                    continue
                if riga[0].upper() in ("TOTALI", "TOTALE"):
                    continue
                if len(riga) >= 2 and riga[1]:
                    risultati.append({
                        "candidato": None,
                        "eletto": False,
                        "voti_candidato": None,
                        "pct_candidato": None,
                        "liste": [estrai_lista(riga[1], riga[2:])],
                    })
    return risultati


def estrai_lista(nome, celle):
    """Da una riga di lista estrae voti, % e seggi (i campi numerici)."""
    voti, pct, seggi = None, None, None
    for c in celle:
        if re.fullmatch(r"[\d.]+", c) and voti is None:
            voti = int(c.replace(".", ""))
        elif re.fullmatch(r"[\d,]+", c) and pct is None and "," in c:
            pct = float(c.replace(",", "."))
        elif re.fullmatch(r"\d+", c) and seggi is None and "," not in c:
            seggi = int(c)
    return {"lista": nome, "voti": voti, "pct": pct, "seggi": seggi}


def parse_risultati(html_page):
    """Tutte le informazioni estraibili dalla pagina dei risultati."""
    tabelle = estrai_tabelle(html_page)
    aff = parse_affluenza(tabelle)
    sch = parse_schede(tabelle)
    cand = parse_candidati(tabelle)
    h3 = re.search(r"<h3[^>]*>(.*?)</h3>", html_page, re.S)
    intestazione = re.sub(r"<[^>]+>", " ", h3.group(1)) if h3 else ""
    intestazione = re.sub(r"\s+", " ", intestazione).strip()
    return {
        "intestazione": intestazione,
        **aff, **sch,
        "candidati": cand,
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Integrazione open data DAIT (anagrafe amministratori)
# --------------------------------------------------------------------------

def integra_dait(csv_path, comuni):
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
    import csv as _csv
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        righe_raw = f.read().splitlines()
    # scarta le prime righe finché non trovo l'intestazione con i nomi
    start = 0
    for i, r in enumerate(righe_raw[:5]):
        if "denominazione_comune" in r and "cognome" in r:
            start = i
            break
    if start == 0 and "denominazione_comune" not in righe_raw[0]:
        print("[!] Intestazione DAIT non trovata nel CSV")
        return {}
    reader = _csv.DictReader(righe_raw[start:], delimiter=";",
                             quoting=_csv.QUOTE_ALL)
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


# --------------------------------------------------------------------------
# Esplorazione dei valori del form (--elenca)
# --------------------------------------------------------------------------

def esplora_livello(sessione, tipo, data, livello, nome_regione,
                    regione_value, provincia_nome):
    """
    Stampa i valori REALI delle <option> del sito per il livello richiesto:
    regioni, province o comuni disponibili per una data. Serve a scoprire i
    valori da passare a --regione/--province senza aprire il browser.
    Ritorna il codice di uscita (0 ok, 1 livello non raggiungibile).
    """
    r = sessione.get(f"{BASE}?tpel={tipo}&dtel={data}", timeout=30)
    r.raise_for_status()
    html_p = r.text
    aree = leggi_select(html_p, "sel_aree")
    if not aree:
        print(f"[!] {data}: nessuna area (probabilmente nessuna elezione "
              f"in questa data per tpel={tipo})")
        return 1
    pp, pv = leggi_onchange(html_p, "sel_aree")
    html_p = scendi_livello(sessione,
                            pp or f"index.php?tpel={tipo}&dtel={data}&es0=S",
                            pv, aree[0][0])

    if livello == "regioni":
        for v, t in leggi_select(html_p, "sel_sezione2"):
            print(f"  {v}  =  {t}")
        return 0

    # livello province/comuni: scegli la regione per testo (o valore)
    scelta = None
    for v, t in leggi_select(html_p, "sel_sezione2"):
        if t.upper() == nome_regione.upper() or (regione_value and v == regione_value):
            scelta = (v, t)
            break
    if scelta is None:
        print(f"[!] Regione '{nome_regione}' non presente per {data}. "
              f"Disponibili (valore = nome):")
        for v, t in leggi_select(html_p, "sel_sezione2"):
            print(f"  {v}  =  {t}")
        return 1
    pp, pv = leggi_onchange(html_p, "sel_sezione2")
    html_p = scendi_livello(sessione, pp, pv, scelta[0])

    if livello == "province":
        for v, t in leggi_select(html_p, "sel_sezione3"):
            print(f"  {v}  =  {t}")
        return 0

    # livello comuni: scegli la provincia per nome
    province = leggi_select(html_p, "sel_sezione3")
    if not province:
        print(f"[!] Nessun livello provincia per {data}: i risultati sono "
              f"già al livello regione ({scelta[1]}).")
        return 1
    scelta_prov = None
    for v, t in province:
        if t.upper() == provincia_nome.upper():
            scelta_prov = (v, t)
            break
    if scelta_prov is None:
        print(f"[!] Provincia '{provincia_nome}' non presente. Disponibili:")
        for v, t in province:
            print(f"  {v}  =  {t}")
        return 1
    pp, pv = leggi_onchange(html_p, "sel_sezione3")
    html_p = scendi_livello(sessione, pp, pv, scelta_prov[0])
    for v, t in leggi_select(html_p, "sel_sezione4"):
        print(f"  {v}  =  {t}")
    return 0


# --------------------------------------------------------------------------
# Download automatico dell'anagrafe DAIT (--dait auto)
# --------------------------------------------------------------------------

DAIT_AMMCOM_URL = "https://dait.interno.gov.it/documenti/ammcom.csv"


def scarica_ammcom():
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


def main():
    ap = argparse.ArgumentParser(
        description="TallyHo — ti porta a spasso nella storia elettorale italiana "
                    "(Archivio Storico DAIT, 1946-oggi)")
    ap.add_argument("--comuni",
                    help="Comuni da cercare, separati da virgola (es. ROMA,MILANO)")
    ap.add_argument("--elenca", choices=["date", "regioni", "province", "comuni"],
                    help="Esplora i valori REALI del form del sito per la data "
                         "scelta (stampa valore = nome delle <option>) e esce: "
                         "serve a scoprire --regione/--province senza aprire "
                         "il browser")
    ap.add_argument("--regione", default=None,
                    help="Valore option della regione (es. 99-lev199). "
                         "OPZIONALE: se omesso viene ricavato automaticamente "
                         "dal nome (--nome-regione). Per scoprirlo: "
                         "--elenca regioni")
    ap.add_argument("--nome-regione", default="LAZIO",
                    help="Nome della regione/circoscrizione da cercare "
                         "(per le elezioni politiche la circoscrizione ha lo "
                         "stesso nome della regione)")
    ap.add_argument("--province", default="ROMA",
                    help="Province ammesse (virgola, per nome). Per i comuni "
                         "di province istituite dopo il 1992, indicare anche "
                         "la provincia storica per coprire le elezioni "
                         "precedenti (es. --province LECCO,COMO: Lecco è stata istituita nel 1992, prima i suoi comuni erano in provincia di Como)")
    ap.add_argument("--tipo", default="G",
                    help="Tipo elezione: G=comunali (default), C=camera, S=senato, "
                         "E=europee, F=referendum, R=regionali, P=provinciali, A=costituente")
    ap.add_argument("--out", default="dati_elezioni",
                    help="Cartella di output (default dati_elezioni)")
    ap.add_argument("--sleep", type=float, default=1.2,
                    help="Secondi tra una data e l'altra (default 1.2)")
    ap.add_argument("--solo-ultima-data", action="store_true",
                    help="Processa solo l'ultima data disponibile (test)")
    ap.add_argument("--data", help="Processa solo questa data (gg/mm/aaaa)")
    ap.add_argument("--dait", metavar="CSV|auto",
                    help="Anagrafe amministratori DAIT da integrare nel JSON "
                         "(sindaci/commissari in carica con date e lista). "
                         "'auto' scarica da solo il file ufficiale "
                         "ammcom.csv dal portale open data del Ministero "
                         "(con cache); oppure passa il percorso di un CSV "
                         "già scaricato")
    args = ap.parse_args()

    province = tuple(p.strip().upper() for p in args.province.split(",") if p.strip())
    os.makedirs(args.out, exist_ok=True)

    sessione = requests.Session()
    sessione.headers.update({"User-Agent": UA})

    # inizializzazione sessione + date
    r = sessione.get(f"{BASE}?tpel={args.tipo}", timeout=30)
    r.raise_for_status()
    date = leggi_date(r.text)
    if not date:
        print("Nessuna data trovata — controllo il formato della pagina.")
        sys.exit(1)
    print(f"[i] {len(date)} date disponibili per tpel={args.tipo} "
          f"({date[0]} .. {date[-1]})")

    if args.data:
        if args.data not in date:
            print(f"[!] Data {args.data} non nell'elenco — esco.")
            sys.exit(1)
        date = [args.data]
    elif args.solo_ultima_data:
        date = date[:1]

    # ---- modalità esplorazione (--elenca): scopre i valori del form -------
    if args.elenca:
        if args.elenca == "date":
            for d in date:
                print(f"  {d}")
            sys.exit(0)
        data_probe = args.data or date[0]
        if args.data is None:
            print(f"[i] Uso la prima data disponibile ({data_probe}) per "
                  f"l'esplorazione; puoi specificarne un'altra con --data.")
        prima_provincia = args.province.split(",")[0].strip().upper()
        codice = sys.exit(esplora_livello(
            sessione, args.tipo, data_probe, args.elenca,
            args.nome_regione, args.regione, prima_provincia))

    if not args.comuni:
        print("[!] Serve --comuni (es. --comuni ROMA,MILANO) oppure "
              "--elenca (per esplorare i valori del sito).")
        sys.exit(2)

    comuni = [c.strip().upper() for c in args.comuni.split(",") if c.strip()]
    risultati = {c: [] for c in comuni}
    log = []

    for i, data in enumerate(date, 1):
        for comune in comuni:
            try:
                html_ris, ctx = trova_comune(
                    sessione, data, comune, args.tipo, args.regione,
                    args.nome_regione, province)
            except Exception as exc:  # noqa: BLE001
                log.append({"data": data, "comune": comune, "esito": "ERRORE",
                            "dettaglio": str(exc)})
                print(f"  [ERR] {data} {comune}: {exc}")
                time.sleep(args.sleep)
                continue
            if html_ris is None:
                log.append({"data": data, "comune": comune, "esito": "NON_VOTATO"})
                time.sleep(args.sleep)
                continue
            try:
                parsed = parse_risultati(html_ris)
            except Exception as exc:  # noqa: BLE001
                log.append({"data": data, "comune": comune, "esito": "ERRORE",
                            "dettaglio": str(exc)})
                print(f"  [ERR] {data} {comune}: {exc}")
                time.sleep(args.sleep)
                continue
            rec = {"data_elezione": data, "tipo": "Comunali",
                   "comune": ctx["comune"], "provincia": ctx["provincia"],
                   **parsed}
            risultati[comune].append(rec)
            n_cand = len(parsed["candidati"])
            print(f"  [OK] {data} {comune}: {n_cand} candidati")
            log.append({"data": data, "comune": comune, "esito": "OK",
                        "candidati": n_cand})
            time.sleep(args.sleep / 2)
        time.sleep(args.sleep)

    # ---- export CSV ----
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(args.out, f"elezioni_{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data_elezione", "comune", "provincia", "elettori",
                    "votanti", "affluenza_pct", "bianche", "non_valide",
                    "candidato", "eletto", "voti_candidato", "pct_candidato",
                    "lista", "voti_lista", "pct_lista", "seggi"])
        for comune in comuni:
            for rec in risultati[comune]:
                for c in rec["candidati"]:
                    if c["liste"]:
                        for l in c["liste"]:
                            w.writerow([rec["data_elezione"], rec["comune"],
                                        rec["provincia"], rec["elettori"],
                                        rec["votanti"], rec["affluenza_pct"],
                                        rec["bianche"], rec["non_valide"],
                                        c["candidato"] or "", c["eletto"],
                                        c["voti_candidato"], c["pct_candidato"],
                                        l["lista"], l["voti"], l["pct"],
                                        l["seggi"]])
                    else:
                        w.writerow([rec["data_elezione"], rec["comune"],
                                    rec["provincia"], rec["elettori"],
                                    rec["votanti"], rec["affluenza_pct"],
                                    rec["bianche"], rec["non_valide"],
                                    c["candidato"] or "", c["eletto"],
                                    c["voti_candidato"], c["pct_candidato"],
                                    "", "", "", ""])
    print(f"\n[+] CSV: {csv_path}")

    # ---- export JSON ----
    json_path = os.path.join(args.out, f"elezioni_{ts}.json")
    payload = {"generato": ts, "comuni": comuni,
               "risultati": risultati, "log": log}
    if args.dait:
        percorso_dait = (scarica_ammcom() if args.dait == "auto"
                         else args.dait)
        payload["amministratori_dait"] = integra_dait(percorso_dait, comuni)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON: {json_path}")

    # ---- riepilogo ----
    for comune in comuni:
        n = len(risultati[comune])
        print(f"[i] {comune}: {n} consultazioni trovate")
    non_vot = sum(1 for x in log if x["esito"] == "NON_VOTATO")
    err = sum(1 for x in log if x["esito"] == "ERRORE")
    print(f"[i] totali: OK {len(log) - non_vot - err} | "
          f"non votato {non_vot} | errori {err}")


if __name__ == "__main__":
    main()
