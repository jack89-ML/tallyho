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

La logica è suddivisa in moduli: `navigazione` (decodifica, lettura del form
e discesa della gerarchia), `parsing` (estrazione dei risultati) ed `export`
(CSV/JSON e integrazione DAIT). Questo modulo contiene solo la CLI (`main`)
e l'esplorazione dei valori (`--elenca`).
"""

import argparse
import os
import sys
import time
from datetime import datetime

import requests

from .costanti import BASE, TIPO_ETICHETTE, UA
from .export import (esporta_csv, esporta_json, integra_dait,
                     scarica_ammcom)
from .navigazione import (leggi_date, leggi_onchange, leggi_select,
                          scendi_livello, trova_comune)
from .parsing import parse_risultati


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
            rec = {"data_elezione": data,
                   "tipo": TIPO_ETICHETTE.get(args.tipo, args.tipo),
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
    esporta_csv(csv_path, comuni, risultati)
    print(f"\n[+] CSV: {csv_path}")

    # ---- export JSON ----
    json_path = os.path.join(args.out, f"elezioni_{ts}.json")
    amministratori = None
    if args.dait:
        percorso_dait = (scarica_ammcom() if args.dait == "auto"
                         else args.dait)
        amministratori = integra_dait(percorso_dait, comuni)
    esporta_json(json_path, comuni, risultati, log, amministratori,
                 generato=ts)
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
