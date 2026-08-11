# estrattore-elezioni-italiane

Estrazione della **serie storica elettorale italiana** dall'
[Archivio Storico delle Elezioni](https://elezionistorico.interno.gov.it) del
Ministero dell'Interno (DAIT) — copertura dal **1946 a oggi**.

Il sito ufficiale è navigabile solo tramite un form JavaScript a più passi
(data → area → regione → … → comune). Questo strumento riproduce
esattamente quella sequenza di chiamate (decodificando i valori compatti
delle `<option>`, es. `18-lev118` → `ne1=18&lev1=18`) e salva i risultati
in **CSV** e **JSON**.

## Perché esiste

- Il progetto [mevalerio/Eligendo-Downloader](https://github.com/mevalerio/Eligendo-Downloader)
  è uno **stub** (nessuna chiamata alle API reali, dati demo locali).
- Le API JSON del portale risultati 2026 (`elezioni.interno.gov.it`) non
  sono interrogabili direttamente (la SPA cattura tutte le route).
- L'archivio storico funziona ed è l'unica fonte ufficiale completa
  (elezioni comunali dal 1970, politiche dal 1946).

## Funzionalità

- [x] Estrazione serie storica per comune (tutte le date disponibili)
- [x] Tipi di elezione: **comunali** (G), **regionali** (R), **provinciali** (P),
      **politiche** Camera/Senato (C/S), **europee** (E), **referendum** (F),
      **Costituente** (A)
- [x] Discesa gerarchica dinamica: regione → provincia → comune (comunali),
      regione con risultati a quel livello (regionali), circoscrizione →
      collegi plurinominali/uninominali (politiche post-2017)
- [x] Gestione automatica delle province storiche (i comuni oggi in provincia
      di Crotone risultavano in provincia di Catanzaro prima del 1992)
- [x] Formato risultati moderno (candidati sindaco + liste) e storico
      (sole liste, sindaco eletto dal consiglio)
- [x] Export CSV (delimitatore `;`, UTF-8 BOM per Excel) e JSON
- [x] Integrazione open data DAIT (`--dait`): amministratori in carica nel JSON
- [x] Ripresa dei run interrotti (i file già scaricati vengono registrati)
- [x] Rispetto del server: pausa configurabile tra le richieste

## Installazione

```bash
git clone <questo-repo>
cd estrattore-elezioni-italiane
python3 -m venv .venv
.venv/bin/pip install -e .
```

Sviluppo/test:

```bash
.venv/bin/pip install -e ".[dev]"
pytest
```

## Uso

```bash
# Serie storica comunale dei 3 comuni del caso (Calabria)
estrattore-elezioni --comuni SAVELLI,VERZINO,CAMPANA

# Equivalente via python -m
python -m estrattore_elezioni --comuni SAVELLI,VERZINO,CAMPANA

# Altro comune, altra regione (Lazio: valore option 12-lev112, nome ROMA)
estrattore-elezioni --comuni ROMA --regione 12-lev112 --nome-regione LAZIO --province ROMA

# Solo una data (test rapido)
estrattore-elezioni --comuni SAVELLI --data 14/05/2023

# Solo l'ultima data disponibile
estrattore-elezioni --solo-ultima-data

# Regionali in Calabria (i risultati sono a livello regione)
estrattore-elezioni --tipo R --comuni SAVELLI,VERZINO,CAMPANA

# Integrazione anagrafe amministratori DAIT nel JSON
estrattore-elezioni --dait ammcom.csv

# Output in una cartella specifica, pausa più lunga
estrattore-elezioni --out ./dati --sleep 2.0
```

### Opzioni

| Opzione | Default | Descrizione |
|---|---|---|
| `--comuni` | SAVELLI,VERZINO,CAMPANA | Comuni da cercare (virgola) |
| `--regione` | `18-lev118` | Valore option della regione (Calabria) |
| `--nome-regione` | `CALABRIA` | Testo della regione/circoscrizione (per le politiche la circoscrizione ha lo stesso nome) |
| `--province` | CROTONE,COSENZA,CATANZARO | Province ammesse (Catanzaro per lo storico pre-1992) |
| `--tipo` | `G` | Tipo elezione: G comunali, R regionali, P provinciali, C camera, S senato, E europee, F referendum, A costituente |
| `--out` | `dati_elezioni` | Cartella di output |
| `--sleep` | `1.2` | Secondi tra una data e l'altra |
| `--data` | — | Processa solo una data (gg/mm/aaaa) |
| `--solo-ultima-data` | — | Solo l'ultima data (test) |
| `--dait CSV` | — | CSV anagrafe amministratori DAIT da integrare nel JSON |

## Formato output

### CSV (`;`)

```
data_elezione;comune;provincia;elettori;votanti;affluenza_pct;bianche;non_valide;candidato;eletto;voti_candidato;pct_candidato;lista;voti_lista;pct_lista;seggi
14/05/2023;SAVELLI;CROTONE;1662;819;49.28;3;9;SPINA FRANCESCO;True;415;51.23;RICOMINCIAMO;415;51.23;7
```

Nelle elezioni storiche (sindaco eletto dal consiglio) la colonna `candidato`
è vuota e restano le liste; nelle **regionali** il dato è a livello regione
(replicato per ogni comune richiesto).

### JSON

Struttura completa con affluenza, schede, candidati e liste per ogni
consultazione, più un log di navigazione (OK / NON_VOTATO / ERRORE) e,
con `--dait`, la sezione `amministratori_dait`.

## Come funziona (per contributori)

Il sito usa un form con `<select>` pilotati da JS:

```html
<select name="sel_sezione2" onchange="carica_pagina('index.php?tpel=G&dtel=...&tpe=R&...','ne1',this.options[this.selectedIndex].value);">
  <option value="18-lev118">CALABRIA</option>
```

I valori delle option sono **codificati** e vanno decodificati:

```
18-lev118        ->  ne1=18&lev1=18        (regione)
97-lev297        ->  ne2=97&lev2=97        (provincia)
970230-lev3230   ->  ne3=970230&lev3=230   (comune: il valore è il suffisso)
I-lev00-levsut00-msN-tpeA -> tpa=I&lev0=0&levsut0=0&ms=N&tpe=A  (area)
```

Lo script segue l'`onchange` di ogni select come farebbe il browser,
mantenendo una sessione HTTP unica, e si ferma al primo livello la cui
pagina contiene già la tabella dei risultati. La pagina dei risultati
contiene tre tabelle: affluenza, schede, e candidati+liste (o sole liste
per il periodo 1970-1985).

## Limiti e note

- Il server non fornisce un'API pubblica: questo strumento automatizza la
  navigazione del form ufficiale; usare con moderazione (`--sleep`).
- Per le **elezioni politiche** il livello minimo pubblicato è il collegio
  uninominale/plurinominale, non il comune: la ricerca per comune non trova
  risultati (limite della fonte, non dello strumento).
- I risultati vanno verificati sul sito ufficiale per usi istituzionali.
- Il dataset `ammcom.csv` dell'[anagrafe amministratori](https://dait.interno.gov.it/elezioni/open-data)
  può essere integrato per incrociare i sindaci con i risultati elettorali.

## Struttura del progetto

```
estrattore-elezioni-italiane/
├── src/estrattore_elezioni/
│   ├── __init__.py      # API pubblica
│   ├── __main__.py      # python -m estrattore_elezioni
│   ├── cli.py           # console script
│   └── estrattore.py    # logica: decodifica, navigazione, parsing
├── tests/               # test unitari (decodifica, parsing — senza rete)
├── examples/            # esempi di output
├── .github/workflows/ci.yml
├── pyproject.toml
└── README.md
```

## Licenza

MIT
