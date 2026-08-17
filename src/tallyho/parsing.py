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


def parse_affluenza(tabelle: list) -> dict:
    """Elettori, votanti, percentuale dalla tabella di riepilogo."""
    out: dict = {"elettori": None, "votanti": None, "affluenza_pct": None}
    for tab in tabelle:
        if tab and tab[0] and "affluenza" in tab[0][0].lower():
            for riga in tab[1:]:
                if len(riga) >= 2:
                    k = riga[0].lower()
                    if k.startswith("elettori"):
                        out["elettori"] = int(riga[1].replace(".", ""))
                    elif k.startswith("votanti"):
                        out["votanti"] = int(riga[1].replace(".", ""))
                        m = re.search(r"([\d,]+)\s*%",
                                      riga[2] if len(riga) > 2 else "")
                        if m:
                            out["affluenza_pct"] = float(
                                m.group(1).replace(",", "."))
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
                        out["bianche"] = int(riga[1].replace(".", ""))
                    elif k.startswith("non valide"):
                        out["non_valide"] = int(riga[1].replace(".", ""))
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


def parse_risultati(html_page: str) -> dict:
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
