"""Parsing della pagina dei risultati: affluenza, schede, candidati e liste."""

import html as html_mod
import re


def pulisci(cella: str) -> str:
    """Testo di una cella, ripulito."""
    t = re.sub(r"<[^>]+>", "", cella)
    t = html_mod.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def estrai_tabelle(html_page: str) -> list:
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


def estrai_lista(nome: str, celle: list) -> dict:
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


def _to_int(cella: str):
    """Converte una cella in intero ignorando i separatori di migliaia;
    ritorna None se il valore non è numerico (mai eccezioni)."""
    try:
        return int(cella.replace(".", ""))
    except (TypeError, ValueError):
        return None


def _parse_perc(cella: str):
    """Percentuale '62,50' o '62,50%' -> float; None se non numerica."""
    m = re.search(r"([\d,]+)\s*%?", cella)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def rileva_turno(html_page: str) -> str:
    """'ballottaggio' se negli header compare 'II turno' (case-insensitive),
    altrimenti '1° turno'."""
    if re.search(r"ii\s+turno", html_page, re.I):
        return "ballottaggio"
    return "1° turno"


def parse_affluenza(tabelle: list) -> dict:
    """Elettori, votanti, percentuale dalla tabella di riepilogo."""
    out: dict = {"elettori": None, "votanti": None, "affluenza_pct": None}
    for tab in tabelle:
        if tab and tab[0] and "affluenza" in tab[0][0].lower():
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("elettori"):
                        out["elettori"] = _to_int(riga[1])
                    elif k.startswith("votanti"):
                        out["votanti"] = _to_int(riga[1])
                        m = re.search(r"([\d,]+)\s*%",
                                      riga[2] if len(riga) > 2 else "")
                        if m:
                            out["affluenza_pct"] = float(
                                m.group(1).replace(",", "."))
    if (out["affluenza_pct"] is None and out["elettori"] is not None
            and out["elettori"] > 0 and out["votanti"] is not None):
        out["affluenza_pct"] = round(out["votanti"] / out["elettori"] * 100, 2)
    return out


def parse_schede(tabelle: list) -> dict:
    """Bianche e non valide."""
    out: dict = {"bianche": None, "non_valide": None}
    for tab in tabelle:
        if tab and tab[0] and "schede" in tab[0][0].lower():
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("bianche"):
                        out["bianche"] = _to_int(riga[1])
                    elif k.startswith("non valide"):
                        out["non_valide"] = _to_int(riga[1])
    return out


def parse_candidati(tabelle: list) -> list:
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
                                           if re.fullmatch(r"[\d.]+", voti)
                                           else None),
                        "pct_candidato": (float(pct.replace(",", "."))
                                          if re.fullmatch(r"[\d,]+", pct)
                                          else None),
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


# --------------------------------------------------------------------------
# Referendum (un quesito per blocco: titolo + tabelle SI/NO)
# --------------------------------------------------------------------------

def _parse_quesito(titolo: str, tabelle: list) -> dict:
    """Estrae i dati di un singolo quesito referendario dalle sue tabelle."""
    q = {"quesito": titolo, "elettori": None, "votanti": None,
         "affluenza_pct": None, "valide": None, "bianche": None,
         "non_valide": None,
         "si": {"voti": None, "pct": None}, "no": {"voti": None, "pct": None}}
    for tab in tabelle:
        if not tab or not tab[0]:
            continue
        header = " ".join(tab[0]).lower()
        if header.startswith("elettori"):
            # tabella di riepilogo: riga "Elettori" -> valore
            for riga in tab:
                if (riga and riga[0].lower().startswith("elettori")
                        and len(riga) > 1):
                    q["elettori"] = _to_int(riga[1])
                    break
        elif "affluenza" in header:
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("votanti"):
                        q["votanti"] = _to_int(riga[1])
                    elif k.startswith("%"):
                        q["affluenza_pct"] = _parse_perc(riga[1])
        elif "schede" in header:
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("valide"):
                        q["valide"] = _to_int(riga[1])
                    elif "non valide" in k:
                        q["non_valide"] = _to_int(riga[1])
                    elif "bianche" in k:
                        q["bianche"] = _to_int(riga[1])
        elif header.startswith("si") and "no" in header:
            # riga voti poi riga percentuali (con % o virgola)
            for riga in tab[1:]:
                if len(riga) < 2:
                    continue
                if "%" in riga[0] or "," in riga[0]:
                    q["si"]["pct"] = _parse_perc(riga[0])
                    q["no"]["pct"] = _parse_perc(riga[1])
                else:
                    q["si"]["voti"] = _to_int(riga[0])
                    q["no"]["voti"] = _to_int(riga[1])
    if (q["affluenza_pct"] is None and q["elettori"] is not None
            and q["elettori"] > 0 and q["votanti"] is not None):
        q["affluenza_pct"] = round(q["votanti"] / q["elettori"] * 100, 2)
    return q


def parse_referendum(html_page: str) -> dict:
    """Parsing specifico dei referendum: una sezione per quesito.

    Ritorna {'quesiti': [ {quesito, elettori, votanti, affluenza_pct,
    valide, bianche, non_valide, si{voti,pct}, no{voti,pct}}, ... ]}.
    """
    match_titoli = list(re.finditer(
        r'<div[^>]*class="[^"]*dati_referendum_titolo_quesito[^"]*"[^>]*>'
        r"(.*?)</div>", html_page, re.S))
    quesiti = []
    for i, m in enumerate(match_titoli):
        titolo = pulisci(m.group(1))
        inizio_blocco = m.end()
        fine_blocco = (match_titoli[i + 1].start()
                       if i + 1 < len(match_titoli) else len(html_page))
        quesiti.append(_parse_quesito(titolo, estrai_tabelle(
            html_page[inizio_blocco:fine_blocco])))
    return {"quesiti": quesiti}


def parse_risultati(html_page: str) -> dict:
    """Tutte le informazioni estraibili dalla pagina dei risultati."""
    h3 = re.search(r"<h3[^>]*>(.*?)</h3>", html_page, re.S)
    intestazione = re.sub(r"<[^>]+>", " ", h3.group(1)) if h3 else ""
    intestazione = re.sub(r"\s+", " ", intestazione).strip()
    turno = rileva_turno(html_page)

    # referendum: struttura a quesiti (SI/NO), niente candidati/liste
    if "dati_referendum_titolo_quesito" in html_page:
        return {
            "intestazione": intestazione,
            "turno": turno,
            "quesiti": parse_referendum(html_page)["quesiti"],
            "elettori": None, "votanti": None, "affluenza_pct": None,
            "bianche": None, "non_valide": None,
            "candidati": [],
        }

    tabelle = estrai_tabelle(html_page)
    aff = parse_affluenza(tabelle)
    sch = parse_schede(tabelle)
    cand = parse_candidati(tabelle)
    return {
        "intestazione": intestazione,
        "turno": turno,
        **aff, **sch,
        "candidati": cand,
    }
