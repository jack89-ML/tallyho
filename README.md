# estrattore-elezioni-italiane

Estrazione della **serie storica elettorale italiana** dall'
[Archivio Storico delle Elezioni](https://elezionistorico.interno.gov.it) del
Ministero dell'Interno (DAIT) — copertura dal **1946 a oggi**.

Il sito ufficiale è navigabile solo tramite un form JavaScript a più passi
(data → area → regione → … → comune). Questo strumento riproduce
esattamente quella sequenza di chiamate (decodificando i valori compatti
delle `<option>`, es. `12-lev112` → `ne1=12&lev1=12`) e salva i risultati
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
- [x] Gestione automatica delle province storiche (i comuni di una provincia
      istituita nel 1992 risultavano nella provincia originaria per le
      elezioni precedenti)
- [x] Formato risultati moderno (candidati + liste) e storico
      (sole liste, amministratori eletti dal consiglio)
- [x] Export CSV (delimitatore `;`, UTF-8 BOM per Excel) e JSON
- [x] Esplorazione dei valori del form (`--elenca`): regioni, province,
      comuni e date reali del sito senza ispezionare il browser
- [x] Valore della regione ricavato automaticamente dal nome
- [x] Integrazione anagrafe amministratori DAIT (`--dait auto` scarica da
      solo il file ufficiale del Ministero, con cache)
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
# Serie storica comunale (es. Roma e Milano)
estrattore-elezioni --comuni ROMA,MILANO

# Equivalente via python -m
python -m estrattore_elezioni --comuni ROMA,MILANO

# Solo una data (test rapido)
estrattore-elezioni --comuni ROMA --data 03/10/2021

# Solo l'ultima data disponibile
estrattore-elezioni --solo-ultima-data

# Regionali (i risultati sono a livello regione)
estrattore-elezioni --tipo R --comuni ROMA --nome-regione LAZIO

# Integrazione anagrafe amministratori DAIT nel JSON
estrattore-elezioni --comuni ROMA --dait ammcom.csv

# Output in una cartella specifica, pausa più lunga
estrattore-elezioni --comuni ROMA --out ./dati --sleep 2.0
```

### Opzioni

| Opzione | Default | Descrizione |
|---|---|---|
| `--comuni` | — | Comuni da cercare, separati da virgola |
| `--elenca` | — | Esplora i valori del form (date, regioni, province, comuni) e esce |
| `--regione` | (auto) | Valore option della regione — opzionale, ricavato dal nome |
| `--nome-regione` | `LAZIO` | Nome della regione/circoscrizione da cercare |
| `--province` | `ROMA` | Province ammesse (per nome, virgola) |
| `--tipo` | `G` | Tipo elezione: G comunali, R regionali, P provinciali, C camera, S senato, E europee, F referendum, A costituente |
| `--out` | `dati_elezioni` | Cartella di output |
| `--sleep` | `1.2` | Secondi tra una data e l'altra |
| `--data` | — | Processa solo una data (gg/mm/aaaa) |
| `--solo-ultima-data` | — | Solo l'ultima data (test) |
| `--dait CSV\|auto` | — | Anagrafe amministratori DAIT nel JSON (`auto` = download automatico) |

## Esplorare i valori senza aprire il browser

I valori di `--regione` e `--province` si scoprono da soli con l'opzione
`--elenca`: interroga il sito e stampa le `<option>` reali del form
(formato `valore = nome`).

```bash
# tutte le date disponibili per le comunali
estrattore-elezioni --elenca date

# regioni che hanno votato il 14/05/2023 (valore = nome)
estrattore-elezioni --elenca regioni --data 14/05/2023

# province della Calabria in quella data
estrattore-elezioni --elenca province --data 14/05/2023 --nome-regione CALABRIA

# comuni della provincia di Crotone in quella data
estrattore-elezioni --elenca comuni --data 14/05/2023 \
    --nome-regione CALABRIA --province CROTONE
```

Output di esempio:

```
  18-lev118  =  CALABRIA
  12-lev112  =  LAZIO
  ...
  97-lev297  =  CROTONE
  ...
  970230-lev3230  =  SAVELLI
```

In pratica **non serve mai conoscere i valori a memoria**: lo script
ricava `--regione` automaticamente dal nome (`--nome-regione`, di default
LAZIO) e `--province` funziona per nome. `--elenca` serve per verificare
quali aree hanno votato in una data (o per esplorare altre regioni).

## Come funziona la serie storica

Lo script non conosce a priori le date di elezione di un comune: le **legge
dal sito**. Il primo `<select>` del form (`sel_date`) contiene tutte le date
disponibili per il tipo di elezione scelto (per le comunali sono oltre 160,
dal 1970 a oggi). Per **ogni data** lo script:

1. seleziona la data nel form;
2. scende la gerarchia (regione → provincia → comune) con le stesse
   chiamate che fa il browser quando clicchi i menu a tendina;
3. se il comune compare nell'elenco del livello finale, scarica la pagina
   dei risultati e la parsa; altrimenti registra l'esito `NON_VOTATO`
   (il comune non ha avuto elezioni in quella data: mandato in corso,
   commissariamento, scioglimento) e passa alla data successiva.

Alla fine il CSV contiene **una riga per ogni lista/candidato di ogni
consultazione in cui il comune ha votato**: è la serie storica completa.
Il log nel JSON distingue `OK`, `NON_VOTATO` ed eventuali `ERRORE`.

## Come funziona `--dait`

L'[anagrafe degli amministratori locali](https://dait.interno.gov.it/elezioni/open-data)
è un open data del Ministero dell'Interno: il file `ammcom.csv` (aggiornato
con cadenza periodica) elenca, per ogni comune, gli amministratori **in
carica** con nome, cognome, carica (sindaco, assessore, consigliere,
commissario…), date di elezione e di entrata in carica, lista.

Due modi di usarlo:

```bash
# 1) automatico: scarica il file ufficiale dal portale del Ministero
#    (cache in ~/.cache/estrattore-elezioni/, ~30 MB una tantum)
estrattore-elezioni --comuni ROMA --dait auto

# 2) manuale: passi un CSV già scaricato (anche filtrato per i comuni)
estrattore-elezioni --comuni ROMA --dait ammcom.csv
```

A quel punto `integra_dait`:
1. legge il CSV (salta le prime righe di titolo e data di aggiornamento);
2. filtra le righe per `denominazione_comune` tra i comuni richiesti;
3. aggiunge al JSON di output una sezione `amministratori_dait` con, per
   ogni comune, l'elenco degli amministratori in carica (carica, nominativo,
   date, lista).

È utile per incrociare i risultati elettorali con chi governa: es. capire
se il sindaco uscente è stato riconfermato o se il comune è sotto
commissariamento.

## Come estrarre la serie storica (comandi pratici)

La serie storica di un comune è l'insieme di tutte le consultazioni in cui
ha votato, dal 1970 (comunali) o dal 1946 (altri tipi) a oggi. Lo script la
estrae da solo iterando su tutte le date disponibili:

```bash
# serie storica COMPLETA di uno o più comuni (tutte le date, tutti i tipi
# selezionati con --tipo; default comunali)
estrattore-elezioni --comuni SAVELLI,VERZINO --nome-regione CALABRIA \
    --province CROTONE,CATANZARO --out dati_elezioni

# stessa cosa, ma salvando anche l'anagrafe degli amministratori nel JSON
estrattore-elezioni --comuni SAVELLI,VERZINO --nome-regione CALABRIA \
    --province CROTONE,CATANZARO --dait auto

# anche le elezioni regionali della zona
estrattore-elezioni --comuni SAVELLI --tipo R --nome-regione CALABRIA

# test rapido: solo l'ultima data (per verificare che tutto funzioni)
estrattore-elezioni --comuni SAVELLI --nome-regione CALABRIA \
    --province CROTONE --solo-ultima-data
```

Cosa produce (nella cartella `--out`):

- `elezioni_<timestamp>.csv` — una riga per ogni lista/candidato di ogni
  consultazione in cui il comune ha votato: data, comune, provincia,
  elettori, votanti, affluenza, bianche, non valide, candidato, eletto,
  voti, %, lista, seggi;
- `elezioni_<timestamp>.json` — la stessa struttura annidata + il log di
  navigazione (OK / NON_VOTATO / ERRORE per ogni data) +, con `--dait`,
  la sezione `amministratori_dait`.

I `NON_VOTATO` nel log sono informativi: il comune non ha avuto elezioni
in quella data (mandato in corso, commissariamento, scioglimento) — la
serie storica è comunque completa perché copre tutte le date possibili.

## Formato output

### CSV (`;`)

```
data_elezione;comune;provincia;elettori;votanti;affluenza_pct;bianche;non_valide;candidato;eletto;voti_candidato;pct_candidato;lista;voti_lista;pct_lista;seggi
03/10/2021;ROMA;ROMA;2359248;1145268;;12389;35356;GUALTIERI ROBERTO;True;299976;27.03;PARTITO DEMOCRATICO;166194;16.38;18
```

Nelle elezioni storiche (amministratori eletti dal consiglio) la colonna
`candidato` è vuota e restano le liste; nelle **regionali** il dato è a
livello regione (replicato per ogni comune richiesto).

### JSON

Struttura completa con affluenza, schede, candidati e liste per ogni
consultazione, più un log di navigazione (OK / NON_VOTATO / ERRORE) e,
con `--dait`, la sezione `amministratori_dait`.

## Come funziona (per contributori)

Il sito usa un form con `<select>` pilotati da JS:

```html
<select name="sel_sezione2" onchange="carica_pagina('index.php?tpel=G&dtel=...&tpe=R&...','ne1',this.options[this.selectedIndex].value);">
  <option value="12-lev112">LAZIO</option>
```

I valori delle option sono **codificati** e vanno decodificati:

```
12-lev112        ->  ne1=12&lev1=12        (regione)
58-lev258        ->  ne2=58&lev2=58        (provincia)
58091-lev558091  ->  ne3=58091&lev3=58091  (comune)
I-lev00-levsut00-msN-tpeA -> tpa=I&lev0=0&levsut0=0&ms=N&tpe=A  (area)
```

Lo script segue l'`onchange` di ogni select come farebbe il browser,
mantenendo una sessione HTTP unica, e si ferma al primo livello la cui
pagina contiene già la tabella dei risultati (così le regionali si fermano
alla regione e le comunali arrivano al comune). La pagina dei risultati
contiene tre tabelle: affluenza, schede, e candidati+liste (o sole liste
per il periodo 1970-1985).

## Limiti e note

- Il server non fornisce un'API pubblica: questo strumento automatizza la
  navigazione del form ufficiale; usare con moderazione (`--sleep`).
- Per le **elezioni politiche** il livello minimo pubblicato è il collegio
  uninominale/plurinominale, non il comune: la ricerca per comune non trova
  risultati (limite della fonte, non dello strumento).
- I risultati vanno verificati sul sito ufficiale per usi istituzionali.

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
├── pyproject.toml
└── README.md
```

## Licenza

MIT
