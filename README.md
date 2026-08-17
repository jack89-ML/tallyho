# TallyHo

<p align="center">
  <img src="assets/logo_tallyho.png" alt="TallyHo" width="320">
</p>

**TallyHo** ti porta a spasso nella storia elettorale italiana — dal 1946
a oggi, comune per comune, senza un solo click a mano.

L'[Archivio Storico delle Elezioni](https://elezionistorico.interno.gov.it)
del Ministero dell'Interno (DAIT) è un tesoro: 70 anni di voti, sindaci,
liste, affluenze e ballottaggi. Peccato che per guardarlo devi cliccare un
form JavaScript a più passi — data, area, regione, provincia, comune — e
ricominciare da capo per ogni data. TallyHo fa i clic al posto tuo:
gli dici **"portami tutto quello che ha votato questo comune"** e lui
scende la gerarchia per **ogni data disponibile**, estrae i risultati e te
li consegna in **CSV** e **JSON**, pronti per l'analisi.

## Perché esiste

L'Archivio Storico delle Elezioni è la fonte ufficiale più completa in
assoluto (elezioni comunali dal 1970, politiche dal 1946), ma è pensato
per la consultazione visiva, non per il download: ogni comune, ogni data
e ogni livello territoriale richiedono una sequenza di clic su un form
JavaScript a più passi. Con oltre 160 date possibili per le sole comunali,
ricostruire a mano la storia elettorale di un comune significa migliaia di
interazioni ripetitive. TallyHo nasce per automatizzare quel percorso:
prende ciò che il sito espone (le stesse chiamate che fa il browser) e lo
trasforma in un dataset strutturato (CSV + JSON), pronto per analisi,
visualizzazioni e ricerche. Uno strumento per chi studia il voto — dal
singolo ricercatore al giornalista di dati — senza dover cliccare
cinquant'anni di elezioni un giorno alla volta.

## Funzionalità

- [x] Estrazione serie storica per comune (tutte le date disponibili)
- [x] Tipi di elezione: **comunali** (G), **regionali** (R), **provinciali** (P),
      **politiche** Camera/Senato (C/S), **europee** (E), **referendum** (F),
      **Costituente** (A)
- [x] Discesa gerarchica dinamica: regione → provincia → comune (comunali),
      regione con risultati a quel livello (regionali), circoscrizione →
      collegi plurinominali/uninominali (politiche post-2017), 5 livelli
      per europee (circoscrizione → regione → provincia → comune) e
      provinciali (regione → provincia → collegio → comune)
- [x] Gestione automatica delle province storiche (i comuni di una provincia
      istituita nel 1992 risultavano nella provincia originaria per le
      elezioni precedenti)
- [x] Formato risultati moderno (candidati + liste) e storico
      (sole liste, amministratori eletti dal consiglio)
- [x] Referendum (F): per ogni quesito, voti SI/NO, percentuali, affluenza
      e schede
- [x] Distinzione del turno: campo `turno` ("1° turno" / "ballottaggio")
      in CSV e JSON
- [x] Affluenza calcolata (fallback `votanti/elettori*100`) quando il sito
      non espone la percentuale
- [x] Export CSV (delimitatore `;`, UTF-8 BOM per Excel) e JSON
- [x] Export aggiuntivi: `--long` (formato tidy per pandas/R), `--xlsx`
      (Excel, richiede `openpyxl`), `--parquet` (richiede `pyarrow`)
- [x] File di configurazione `--config` (TOML/YAML) per riusare le opzioni
- [x] Esplorazione dei valori del form (`--elenca`): regioni, province,
      comuni e date reali del sito senza ispezionare il browser
- [x] Valore della regione ricavato automaticamente dal nome
- [x] Integrazione anagrafe amministratori DAIT (`--dait auto` scarica da
      solo il file ufficiale del Ministero, con cache)
- [x] Rispetto del server: pausa configurabile tra le richieste

> **Nuovi qui?** C'è un [cheatsheet](CHEATSHEET.md) con i comandi
> essenziali spiegati passo passo.

## Roadmap (stato)

```
                                TALLYHO — STATO IMPLEMENTAZIONI
   ● = fatto   ◐ = in corso   ○ = da fare

   CORE
   ●── Estrazione serie storica per comune (tutte le date)
   ●── Tipi di elezione: G R P C S E F A (comunali→costituente)
   ●── Parser referendum (SI/NO, per quesito)
   ●── Parsing regionali (candidati presidenti + liste collegate)
   ●── Flag turno (1° turno / ballottaggio)
   ●── Gerarchia dinamica fino a 5 livelli (europee, provinciali)
   ●── Province storiche (pre-1992)
   ●── Affluenza fallback (votanti/elettori*100)
   ●── Gestione errori: OK / NON_VOTATO / ERRORE + pausa uniforme

   EXPORT
   ●── CSV (UTF-8 BOM, ;) · JSON · --long (tidy pandas/R)
   ●── --xlsx (openpyxl) · --parquet (pyarrow)
   ◐── Report Markdown per comune (agenti LLM / KB)   [P6]

   ROBUSTEZZA
   ●── Cache dei form in SQLite (~/.cache/tallyho)     [P2]
   ●── Retry con backoff (2/4/8 s)                     [P2]
   ◐── Catena condivisa tra comuni (~3x meno richieste) [P2]
   ●── Rilevamento cambi del sito (exit 3 se `sel_date` manca) [P3]
   ○── CI attivo (GitHub Actions) — serve refresh token [P1]

   TERRITORIO E ANALYTICS
   ○── Dataset builder --provincia / --tutti-comuni    [P4]
   ○── Aggregazione provincia/regione (tallyho-aggrega) [P4]
   ○── Swing + volatilità Pedersen                     [P5]
   ○── Join ISTAT popolazione (affluenza normalizzata) [P5]
   ○── Clustering comuni · GIS GeoJSON · grafici       [P5]

   DISTRIBUZIONE
   ●── Zenodo + DOI 10.5281/zenodo.21979207 (v1.0.0)   [P3]
   ○── PyPI (pip install tallyho)                      [P6]
   ○── API locale FastAPI                              [P6]
   ○── README EN + Contributing                        [P3]
```

Dettaglio delle singole voci (priorità, stato, note operative):
vedi [ROADMAP.md](ROADMAP.md).

## Implementazioni in dettaglio

### Estrazione
- **Serie storica completa**: tutte le date disponibili per comune, dal
  1970 (comunali) o 1946 (altri tipi) a oggi, in un solo comando.
- **Tipi di elezione**: comunali (G), regionali (R), provinciali (P),
  politiche Camera/Senato (C/S), europee (E), referendum (F), costituente
  (A).
- **Referendum**: per ogni quesito vengono estratti titolo, elettori,
  votanti e %, valide/bianche/non valide, voti SI e NO con percentuali.
- **Regionali**: candidati presidenti (righe `leader`) e liste collegate,
  con esito eletto, voti, % e seggi; i totali di coalizione e le righe
  "LISTE CIRCOSCRIZIONALI" del TOTALE vengono ignorati.
- **Gerarchia dinamica**: la discesa si adatta al numero reale di livelli
  della pagina (fino a 5: circoscrizione → regione → provincia → collegio →
  comune), quindi europee e provinciali funzionano come comunali.
- **Province storiche**: i comuni di province istituite dopo il 1992
  risultano nella provincia originaria per le elezioni precedenti
  (es. `--province LECCO,COMO`).
- **Turno**: ogni consultazione è marcata `1° turno` o `ballottaggio`,
  rilevato dagli header delle tabelle del sito ("II turno").

### Export
- **CSV**: delimitatore `;`, BOM UTF-8 (apre correttamente in Excel),
  una riga per lista/candidato.
- **JSON**: struttura annidata con log di navigazione
  (OK / NON_VOTATO / ERRORE per ogni data).
- **`--long`**: CSV tidy con una riga per osservazione (livelli
  scheda/candidato/lista) pronto per pandas e R senza post-processing.
- **`--xlsx`** e **`--parquet`**: richiedono i pacchetti opzionali
  (`pip install "tallyho[xlsx]"` / `"tallyho[parquet]"`).
- **`--dait`**: integra l'anagrafe amministratori DAIT (sindaci,
  commissari, assessori in carica con date e lista) nel JSON.

### Configurazione
- **`--config file.toml`** (o `.yaml`): default riusabili per tutte le
  opzioni; la riga di comando ha sempre la precedenza.
- **`--no-cache`** / **`--cache-ttl`**: controllo della cache dei form.

### Cache e rispetto del server
- **Cache SQLite** (`~/.cache/tallyho/cache.db`): le pagine del form
  scaricate vengono riusate per 7 giorni (default), con un risparmio
  enorme su dataset grandi. Statistiche a fine run
  (`cache: N/N richieste servite da cache`).
- **Pausa configurabile** (`--sleep`, default 1.2 s) applicata tra le
  date e sui rami di errore/NON_VOTATO: nessun burst di richieste.

### Qualità e test
- **Architettura modulare**: `costanti` / `navigazione` / `parsing` /
  `export` / `cache` / `tallyho` (CLI). API pubblica in `__init__.py`.
- **83 test** (offline, senza rete) + test di integrazione opzionale
  (`-m integration`) contro il sito reale; fixture HTML reali in
  `tests/fixtures/`.
- **README EN** in programma per i contributori internazionali.

## Installazione

```bash
git clone https://github.com/jack89-ML/tallyho
cd tallyho
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
tallyho --comuni ROMA,MILANO

# Equivalente via python -m
python -m tallyho --comuni ROMA,MILANO

# Solo una data (test rapido)
tallyho --comuni ROMA --data 03/10/2021

# Solo l'ultima data disponibile
tallyho --solo-ultima-data

# Regionali (i risultati sono a livello regione)
tallyho --tipo R --comuni ROMA --nome-regione LAZIO

# Integrazione anagrafe amministratori DAIT nel JSON
tallyho --comuni ROMA --dait ammcom.csv

# Output in una cartella specifica, pausa più lunga
tallyho --comuni ROMA --out ./dati --sleep 2.0
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
| `--long` | off | Esporta anche il CSV in formato tidy (una riga per osservazione, pronto per pandas/R) |
| `--xlsx` | off | Esporta anche in Excel (.xlsx) — richiede `openpyxl` (`pip install "tallyho[xlsx]"`) |
| `--parquet` | off | Esporta anche in Parquet — richiede `pyarrow` (`pip install "tallyho[parquet]"`) |
| `--config` | — | File di configurazione TOML/YAML con i default delle opzioni (la CLI ha precedenza) |

## Esplorare i valori senza aprire il browser

I valori di `--regione` e `--province` si scoprono da soli con l'opzione
`--elenca`: interroga il sito e stampa le `<option>` reali del form
(formato `valore = nome`).

```bash
# tutte le date disponibili per le comunali
tallyho --elenca date

# regioni che hanno votato il 14/05/2023 (valore = nome)
tallyho --elenca regioni --data 14/05/2023

# province della Toscana in quella data
tallyho --elenca province --data 14/05/2023 --nome-regione TOSCANA

# comuni della provincia di Firenze in quella data
tallyho --elenca comuni --data 14/05/2023 \
    --nome-regione TOSCANA --province FIRENZE
```

Output di esempio:

```
  09-lev19   =  TOSCANA
  12-lev112  =  LAZIO
  ...
  048-lev248 =  FIRENZE
  ...
  48017-lev348017  =  EMPOLI
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
#    (cache in ~/.cache/tallyho/, ~30 MB una tantum)
tallyho --comuni ROMA --dait auto

# 2) manuale: passi un CSV già scaricato (anche filtrato per i comuni)
tallyho --comuni ROMA --dait ammcom.csv
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
tallyho --comuni FIRENZE,PRATO --nome-regione TOSCANA \
    --province FIRENZE,PRATO --out dati_elezioni

# stessa cosa, ma salvando anche l'anagrafe degli amministratori nel JSON
tallyho --comuni FIRENZE,PRATO --nome-regione TOSCANA \
    --province FIRENZE,PRATO --dait auto

# anche le elezioni regionali della zona
tallyho --comuni FIRENZE --tipo R --nome-regione TOSCANA

# test rapido: solo l'ultima data (per verificare che tutto funzioni)
tallyho --comuni FIRENZE --nome-regione TOSCANA \
    --province FIRENZE --solo-ultima-data
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

### Referendum (CSV)

Per i referendum (`--tipo F`) il CSV contiene **una riga per quesito per
ciascuna opzione SI e NO**:

- `candidato` = titolo del quesito (es. "Q1. Test");
- `lista` = `SI` oppure `NO`;
- `voti_lista` / `pct_lista` = voti e percentuale dell'opzione, ripetuti
  anche in `voti_candidato` / `pct_candidato`;
- le colonne base (`elettori`, `votanti`, `affluenza_pct`, `bianche`,
  `non_valide`) riportano i valori del quesito;
- `eletto` e `seggi` restano vuoti.

Il campo `valide` (schede valide del quesito) **resta solo nel JSON**: non
compare nel CSV.

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
- Prima di un uso esteso, verifica `robots.txt` e i termini d'uso del sito
  (`elezionistorico.interno.gov.it`) e rispettane le eventuali limitazioni:
  l'uso moderato già previsto non sostituisce la conformità alle condizioni
  del portale.
- Per le **elezioni politiche** il livello minimo pubblicato è il collegio
  uninominale/plurinominale, non il comune: la ricerca per comune non trova
  risultati (limite della fonte, non dello strumento).
- I risultati vanno verificati sul sito ufficiale per usi istituzionali.

## Struttura del progetto

```
tallyho/
├── src/tallyho/
│   ├── costanti.py      # costanti condivise (BASE, UA, DAIT_AMMCOM_URL, TIPO_ETICHETTE)
│   ├── navigazione.py   # decodifica opzioni/area, leggi_select/onchange/date, scendi_livello, trova_comune
│   ├── parsing.py       # estrai_tabelle/liste, parse_affluenza/schede/candidati/risultati, parse_referendum, parse_candidati_regionali
│   ├── export.py        # esporta_csv/json/long/xlsx/parquet, scarica_ammcom, integra_dait
│   ├── tallyho.py       # main() e logica CLI
│   ├── __init__.py      # API pubblica
│   ├── cli.py           # entry point (console script)
│   └── __main__.py      # entry point (python -m tallyho)
├── tests/               # test unitari (decodifica, parsing, export, config — senza rete)
│   └── fixtures/        # pagine HTML reali del sito (per i test di parsing)
├── examples/            # esempi di output
├── CHEATSHEET.md        # guida rapida per chi inizia
├── pyproject.toml
└── README.md
```

## Licenza

MIT

## Citazione

I dati esposti provengono dall'Archivio Storico delle Elezioni del
Ministero dell'Interno (DAIT), fonte pubblica e ufficiale:
[elezionistorico.interno.gov.it](https://elezionistorico.interno.gov.it).

Chi utilizza TallyHo — o i dataset da esso generati — in ricerche,
pubblicazioni, articoli, tesi o progetti accademici è tenuto a citare
lo strumento, ad esempio come segue:

> Peracchio, Jacopo (2026). *TallyHo*: serie storica elettorale italiana,
> comune per comune (Versione 1.0.0) [Software].
> https://doi.org/10.5281/zenodo.21979207

In BibTeX:

```bibtex
@software{TallyHo,
  author = {Peracchio, Jacopo},
  title = {{TallyHo}: serie storica elettorale italiana, comune per comune},
  year = {2026},
  version = {1.0.0},
  doi = {10.5281/zenodo.21979207},
  url = {https://github.com/jack89-ML/tallyho}
}
```

Il file `CITATION.cff` nella radice del repository abilita il pulsante
**Cite this repository** su GitHub, che genera la citazione nei formati
APA e BibTeX.

Ogni release di TallyHo è inoltre archiviata su
[Zenodo](https://zenodo.org) (servizio CERN di archiviazione per la
ricerca) con un **DOI permanente**: la versione 1.0.0 ha il DOI
[10.5281/zenodo.21979207](https://doi.org/10.5281/zenodo.21979207).
Il DOI identifica la versione archiviata in modo stabile, anche se il
link a GitHub cambiasse.
