"""Navigazione della gerarchia territoriale del form (area -> regione ->
provincia -> comune) e decodifica dei valori delle <option>."""

import re
from typing import Optional

from .costanti import BASE
from .parsing import estrai_tabelle


# --------------------------------------------------------------------------
# Decodifica dei valori delle <option> (replica esatta della funzione JS
# `carica_pagina` del sito: la variabile è lunga 4 caratteri dopo il primo
# trattino, il valore è tutto ciò che segue).
# --------------------------------------------------------------------------

def decodifica_opzione(valore: str) -> tuple:
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


def decodifica_area(valore: str) -> Optional[str]:
    """Decodifica 'I-lev00-levsut00-msN-tpeA' -> stringa query completa.

    Formato: <tpa>-<var><val>-<var><val>-<var><val>-<var><val> con variabili
    di lunghezza fissa (lev0=4, levsut0=7, ms=2, tpe=3). Ritorna None su
    input malformati (robustezza su pagine anomale).
    """
    parti = valore.split("-")
    if len(parti) < 5:
        return None
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

def leggi_select(html_page: str, nome: str) -> list:
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


def leggi_onchange(html_page: str, nome: str) -> tuple:
    """Ritorna (page_path, page_var) dall'onchange di un select."""
    m = re.search(r'<select name="' + nome + r'"[^>]*?onchange="'
                  r"carica_pagina\('([^']*)','([^']*)',", html_page)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def leggi_date(html_page: str) -> list:
    """Tutte le date disponibili per il tipo di elezione scelto."""
    return [t for _, t in leggi_select(html_page, "sel_date")]


# --------------------------------------------------------------------------
# Navigazione della gerarchia territoriale
# --------------------------------------------------------------------------

def scendi_livello(sessione, page_path: str, page_var: str, valore: str) -> str:
    """Aggiunge il livello selezionato alla URL e carica la pagina."""
    if page_var == "tpa":
        qs = decodifica_area(valore) or ""
    else:
        p1, var2, p2 = decodifica_opzione(valore)
        qs = f"&{page_var}={p1}&{var2}={p2}"
    url = BASE + ("?" + page_path if page_path else "") + qs
    url = url.replace("?index.php?", "?")  # normalizzazione
    if not url.startswith("http"):
        url = "https://elezionistorico.interno.gov.it/" + url.lstrip("/")
    r = sessione.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def trova_comune(sessione, data, comune_target, tipo, regione_value,
                 nome_regione, province_target):
    """
    Percorre data -> area -> ... -> comune in modo dinamico, adattandosi alla
    gerarchia del tipo di elezione:
      - comunali/regionali: area Italia -> regione -> (provincia ->) comune
      - politiche (C/S): area Italia -> circoscrizione (testo == nome
        regione) -> provincia -> comune
      - europee (E): area -> circoscrizione -> regione -> provincia -> comune
      - provinciali (P): area -> regione -> provincia -> collegio -> comune
    La discesa è dinamica: legge i `sel_sezioneN` disponibili nella pagina
    (fino a 5 livelli) invece di assumere una gerarchia fissa.
    Ritorna (html_risultati, contesto) se l'area ha votato, altrimenti
    (None, None).
    """
    comune_target = comune_target.upper()
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

    # passo 4+: discesa dinamica fino al comune (sel_sezione3 .. sel_sezione5)
    return _scendi_fino_a_comune(sessione, html_p, 3, comune_target,
                                 province_target, contesto)


def _scendi_fino_a_comune(sessione, html_p, livello, comune_target,
                          province_target, contesto):
    """Scende i livelli sel_sezione{livello}..5 fino al comune target.

    A ogni livello: se la pagina ha già i risultati si ferma; altrimenti
    legge il select successivo e sceglie il comune (se presente) o le
    province note (o tutte le opzioni come fallback per gerarchie diverse).
    Ritorna (html_risultati, contesto) oppure (None, contesto).
    """
    if pagina_ha_risultati(html_p):
        return html_p, contesto
    sel_nome = f"sel_sezione{livello}"
    opzioni = leggi_select(html_p, sel_nome)
    if not opzioni:
        return (html_p, contesto) if pagina_ha_risultati(html_p) else (None, None)
    pp, pv = leggi_onchange(html_p, sel_nome)

    # 1) livello comune: opzione con testo == comune target
    for v, t in opzioni:
        if t.upper() == comune_target:
            html_giu = scendi_livello(sessione, pp, pv, v)
            contesto["comune"] = t
            if pagina_ha_risultati(html_giu):
                return html_giu, contesto
            return _scendi_fino_a_comune(sessione, html_giu, livello + 1,
                                         comune_target, province_target,
                                         contesto)

    # 2) livello provincia o intermedio: province note, altrimenti tutte le
    #    opzioni (gerarchie diverse: collegi plurinominali, ripartizioni...)
    province = [(v, t) for v, t in opzioni if t.upper() in province_target]
    candidate = province or opzioni
    for v, t in candidate:
        html_giu = scendi_livello(sessione, pp, pv, v)
        ctx = dict(contesto)
        if province:
            ctx["provincia"] = t
        res = _scendi_fino_a_comune(sessione, html_giu, livello + 1,
                                    comune_target, province_target, ctx)
        if res[0] is not None:
            return res
    return None, None


def pagina_ha_risultati(html_page: str) -> bool:
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
