# TallyHo

<p align="center">
  <img src="assets/logo_tallyho.png" alt="TallyHo" width="320">
</p>

**TallyHo** walks you through Italian electoral history — from 1946 to
today, municipality by municipality, without a single manual click.

The Ministry of the Interior's [Historical Archive of Elections](https://elezionistorico.interno.gov.it)
(DAIT) is a treasure: 70 years of votes, mayors, lists, turnouts and
run-offs. The catch is that to consult it you have to click through a
multi-step JavaScript form — date, area, region, province, municipality —
and start over for every date. TallyHo does the clicking for you: you tell
it **"bring me everything this municipality has ever voted on"** and it
descends the hierarchy for **every available date**, extracts the results
and hands them to you as **CSV** and **JSON**, ready for analysis.

## Why it exists

The Historical Archive of Elections is the most complete official source
there is (municipal elections since 1970, general elections since 1946),
but it is designed for visual consultation, not for download: every
municipality, every date and every territorial level require a sequence of
clicks on a multi-step JavaScript form. With more than 160 possible dates
for municipal elections alone, reconstructing a municipality's electoral
history by hand means thousands of repetitive interactions. TallyHo exists
to automate that path: it takes what the site exposes (the very same calls
the browser makes) and turns it into a structured dataset (CSV + JSON),
ready for analysis, visualisations and research. A tool for anyone who
studies voting — from the individual researcher to the data journalist —
without having to click through fifty years of elections one day at a time.

## Features

- [x] Historical series extraction for a municipality (all available dates)
- [x] Election types: **municipal** (G), **regional** (R), **provincial** (P),
      **general** Chamber/Senate (C/S), **European** (E), **referendum** (F),
      **Constituent Assembly** (A)
- [x] Dynamic hierarchical descent: region → province → municipality
      (municipal), region with results at that level (regional),
      constituency → multi-member/single-member colleges (general
      post-2017), 5 levels for European (constituency → region → province →
      municipality) and provincial (region → province → college →
      municipality)
- [x] Automatic handling of historical provinces (the municipalities of a
      province established in 1992 were listed under the original province
      for earlier elections)
- [x] Modern result format (candidates + lists) and historical format
      (lists only, administrators elected by the council)
- [x] Referendum (F): for each question, YES/NO votes, percentages, turnout
      and ballots
- [x] Round distinction: `turno` field ("1° turno" / "ballottaggio")
      in CSV and JSON
- [x] Calculated turnout (fallback `votanti/elettori*100`) when the site
      does not expose the percentage
- [x] CSV export (`;` delimiter, UTF-8 BOM for Excel) and JSON
- [x] Extra exports: `--long` (tidy format for pandas/R), `--xlsx`
      (Excel, requires `openpyxl`), `--parquet` (requires `pyarrow`)
- [x] `--config` file (TOML/YAML) to reuse options
- [x] Form value exploration (`--elenca`): regions, provinces,
      municipalities and real dates from the site without inspecting the
      browser
- [x] Region value derived automatically from the name
- [x] DAIT administrators register integration (`--dait auto` downloads the
      Ministry's official file on its own, with cache)
- [x] Respect for the server: configurable pause between requests

> **New here?** There's a [cheatsheet](CHEATSHEET.md) with the essential
> commands explained step by step.

## Roadmap (status)

See [ROADMAP.md](ROADMAP.md) for the full, prioritised list. In short:

- **Done**: historical series extraction, all election types (G R P C S E
  F A), referendum parser, regional parsing, round flag, dynamic hierarchy
  (up to 5 levels), historical provinces, turnout fallback, CSV/JSON/
  `--long`/`--xlsx`/`--parquet` exports, SQLite form cache, retry with
  backoff, site-change detection, Zenodo archive + DOI.
- **In progress**: Markdown report per municipality, shared descent chain
  across municipalities.
- **Planned**: dataset builder, provincial/regional aggregation,
  swing/Pedersen volatility, ISTAT population join, GIS export, PyPI
  publication, local FastAPI API.

## Installation

```bash
git clone https://github.com/jack89-ML/tallyho
cd tallyho
python3 -m venv .venv
.venv/bin/pip install -e .
```

Development/test:

```bash
.venv/bin/pip install -e ".[dev]"
pytest
```

## Usage

```bash
# Municipal historical series (e.g. Rome and Milan)
tallyho --comuni ROMA,MILANO

# Equivalent via python -m
python -m tallyho --comuni ROMA,MILANO

# A single date (quick test)
tallyho --comuni ROMA --data 03/10/2021

# Only the latest available date
tallyho --solo-ultima-data

# Regional (results are at region level)
tallyho --tipo R --comuni ROMA --nome-regione LAZIO

# DAIT administrators register integration in the JSON
tallyho --comuni ROMA --dait ammcom.csv

# Output to a specific folder, longer pause
tallyho --comuni ROMA --out ./dati --sleep 2.0
```

### Options

| Option | Default | Description |
|---|---|---|
| `--comuni` | — | Municipalities to search, comma-separated |
| `--elenca` | — | Explore form values (dates, regions, provinces, municipalities) and exit |
| `--regione` | (auto) | Region option value — optional, derived from the name |
| `--nome-regione` | `LAZIO` | Name of the region/constituency to search |
| `--province` | `ROMA` | Allowed provinces (by name, comma) |
| `--tipo` | `G` | Election type: G municipal, R regional, P provincial, C chamber, S senate, E European, F referendum, A constituent |
| `--out` | `dati_elezioni` | Output folder |
| `--sleep` | `1.2` | Seconds between one date and the next |
| `--data` | — | Process only this date (dd/mm/yyyy) |
| `--solo-ultima-data` | — | Only the latest date (test) |
| `--dait CSV\|auto` | — | DAIT administrators register in the JSON (`auto` = automatic download) |
| `--long` | off | Also export the CSV in tidy format (one row per observation, ready for pandas/R) |
| `--xlsx` | off | Also export to Excel (.xlsx) — requires `openpyxl` (`pip install "tallyho[xlsx]"`) |
| `--parquet` | off | Also export to Parquet — requires `pyarrow` (`pip install "tallyho[parquet]"`) |
| `--config` | — | TOML/YAML config file with the option defaults (the CLI takes precedence) |

## Explore the values without opening the browser

The values of `--regione` and `--province` are discovered on their own with
the `--elenca` option: it queries the site and prints the real `<option>`s
of the form (`value = name` format).

```bash
# all available dates for municipal elections
tallyho --elenca date

# regions that voted on 14/05/2023 (value = name)
tallyho --elenca regioni --data 14/05/2023

# provinces of Tuscany on that date
tallyho --elenca province --data 14/05/2023 --nome-regione TOSCANA

# municipalities of the province of Florence on that date
tallyho --elenca comuni --data 14/05/2023 \
    --nome-regione TOSCANA --province FIRENZE
```

Example output:

```
  09-lev19   =  TOSCANA
  12-lev112  =  LAZIO
  ...
  048-lev248 =  FIRENZE
  ...
  48017-lev348017  =  EMPOLI
```

In practice **you never need to know the values by heart**: the script
derives `--regione` automatically from the name (`--nome-regione`, default
LAZIO) and `--province` works by name. `--elenca` is for checking which
areas voted on a given date (or for exploring other regions).

## How the historical series works

The script does not know a municipality's election dates in advance: it
**reads them from the site**. The first `<select>` of the form (`sel_date`)
contains all the dates available for the chosen election type (for municipal
elections there are more than 160, from 1970 to today). For **each date**
the script:

1. selects the date in the form;
2. descends the hierarchy (region → province → municipality) with the same
   calls the browser makes when you click the dropdowns;
3. if the municipality appears in the final-level list, it downloads and
   parses the results page; otherwise it records the `NON_VOTATO` outcome
   (the municipality had no elections on that date: mandate in progress,
   receivership, dissolution) and moves on to the next date.

In the end the CSV contains **one row per list/candidate of every election
in which the municipality voted**: the complete historical series. The log
in the JSON distinguishes `OK`, `NON_VOTATO` and any `ERRORE`.

## How `--dait` works

The [register of local administrators](https://dait.interno.gov.it/elezioni/open-data)
is an open data set of the Ministry of the Interior: the `ammcom.csv` file
(updated periodically) lists, for each municipality, the administrators
**currently in office** with first name, surname, role (mayor, assessor,
councillor, commissioner…), election and appointment dates, list.

Two ways to use it:

```bash
# 1) automatic: downloads the official file from the Ministry portal
#    (cache in ~/.cache/tallyho/, ~30 MB one-off)
tallyho --comuni ROMA --dait auto

# 2) manual: pass an already-downloaded CSV (even filtered to the municipalities)
tallyho --comuni ROMA --dait ammcom.csv
```

At that point `integra_dait`:
1. reads the CSV (skips the leading title and update-date rows);
2. filters rows by `denominazione_comune` among the requested municipalities;
3. adds an `amministratori_dait` section to the output JSON with, for each
   municipality, the list of administrators in office (role, name, dates,
   list).

It is useful for cross-referencing election results with who governs: e.g.
understanding whether the outgoing mayor was re-confirmed or whether the
municipality is under receivership.

## Output format

### CSV (`;`)

```
data_elezione;comune;provincia;elettori;votanti;affluenza_pct;bianche;non_valide;candidato;eletto;voti_candidato;pct_candidato;lista;voti_lista;pct_lista;seggi
03/10/2021;ROMA;ROMA;2359248;1145268;;12389;35356;GUALTIERI ROBERTO;True;299976;27.03;PARTITO DEMOCRATICO;166194;16.38;18
```

In historical elections (administrators elected by the council) the
`candidato` column is empty and only the lists remain; in **regional**
elections the data is at region level (replicated for each requested
municipality).

### Referendum (CSV)

For referendums (`--tipo F`) the CSV contains **one row per question per
YES and NO option**:

- `candidato` = question title (e.g. "Q1. Test");
- `lista` = `SI` or `NO`;
- `voti_lista` / `pct_lista` = votes and percentage of the option, repeated
  also in `voti_candidato` / `pct_candidato`;
- the base columns (`elettori`, `votanti`, `affluenza_pct`, `bianche`,
  `non_valide`) report the question's values;
- `eletto` and `seggi` stay empty.

The `valide` field (valid ballots of the question) **stays only in the
JSON**: it does not appear in the CSV.

### JSON

Full structure with turnout, ballots, candidates and lists for each
election, plus a navigation log (OK / NON_VOTATO / ERRORE) and, with
`--dait`, the `amministratori_dait` section.

## How it works (for contributors)

The site uses a form with JS-driven `<select>`s:

```html
<select name="sel_sezione2" onchange="carica_pagina('index.php?tpel=G&dtel=...&tpe=R&...','ne1',this.options[this.selectedIndex].value);">
  <option value="12-lev112">LAZIO</option>
```

The option values are **encoded** and must be decoded:

```
12-lev112        ->  ne1=12&lev1=12        (region)
58-lev258        ->  ne2=58&lev2=58        (province)
58091-lev558091  ->  ne3=58091&lev3=58091  (municipality)
I-lev00-levsut00-msN-tpeA -> tpa=I&lev0=0&levsut0=0&ms=N&tpe=A  (area)
```

The script follows the `onchange` of each select as the browser would,
keeping a single HTTP session, and stops at the first level whose page
already contains the results table (so regional elections stop at the region
and municipal elections reach the municipality). The results page contains
three tables: turnout, ballots, and candidates+lists (or lists only for the
1970-1985 period).

## Quality and tests

- **Modular architecture**: `costanti` / `navigazione` / `parsing` /
  `export` / `cache` / `tallyho` (CLI). Public API in `__init__.py`.
- **83 tests** (offline, no network) + optional integration tests
  (`-m integration`) against the real site; real HTML fixtures in
  `tests/fixtures/`.
- **Live integration tests across 5 election types (G/R/F/E/P)**, run
  explicitly with `pytest -m integration`.

## Limits and notes

- The server provides no public API: this tool automates the official
  form's navigation; use in moderation (`--sleep`).
- Before extended use, check `robots.txt` and the terms of use of the site
  (`elezionistorico.interno.gov.it`) and respect any limitations: the
  moderation already provided does not replace compliance with the portal's
  conditions.
- For **general elections** the minimum level published is the
  single-member/multi-member college, not the municipality: searching by
  municipality finds no results (a limitation of the source, not of the
  tool).
- Results should be verified on the official site for institutional use.

## Project structure

```
tallyho/
├── src/tallyho/
│   ├── costanti.py      # shared constants (BASE, UA, DAIT_AMMCOM_URL, TIPO_ETICHETTE)
│   ├── navigazione.py   # option/area decoding, leggi_select/onchange/date, scendi_livello, trova_comune
│   ├── parsing.py       # estrai_tabelle/liste, parse_affluenza/schede/candidati/risultati, parse_referendum, parse_candidati_regionali
│   ├── export.py        # esporta_csv/json/long/xlsx/parquet, scarica_ammcom, integra_dait
│   ├── tallyho.py       # main() and CLI logic
│   ├── __init__.py      # public API
│   ├── cli.py           # entry point (console script)
│   └── __main__.py      # entry point (python -m tallyho)
├── tests/               # unit tests (decoding, parsing, export, config — offline)
│   └── fixtures/        # real HTML pages from the site (for parsing tests)
├── examples/            # output examples
├── CHEATSHEET.md        # quick guide for newcomers
├── pyproject.toml
└── README.md
```

## Contributing

Contributions are welcome. Before opening a PR:

- **Report a bug**: open an [issue](https://github.com/jack89-ML/tallyho/issues)
  describing the command you ran, the election type (`--tipo`), the date and
  the expected vs. actual output. If possible, attach a saved HTML page (the
  fixtures in `tests/fixtures/` help reproduce without network).
- **Propose an improvement**: open an issue to discuss it before writing
  code; check the [ROADMAP](ROADMAP.md) for priorities.
- **Tests are mandatory**: every PR must pass `pytest` (offline tests run
  without network; live integration tests are excluded by default and
  require `pytest -m integration`). Add tests for new code.
- **No multiline sed/awk**: file changes must be exact patches (no fragile
  regex replacements).
- **Style**: Italian for comments, messages and output; English only for
  README.en.md. Follow the existing code style.

PRs that do not follow these rules are not considered.

## License

MIT

## Citation

The exposed data comes from the Ministry of the Interior's Historical
Archive of Elections (DAIT), a public and official source:
[elezionistorico.interno.gov.it](https://elezionistorico.interno.gov.it).

Anyone using TallyHo — or the datasets generated from it — in research,
publications, articles, theses or academic projects is required to cite the
tool, for example as follows:

> Peracchio, Jacopo (2026). *TallyHo*: serie storica elettorale italiana,
> comune per comune (Version 1.0.0) [Software].
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

The `CITATION.cff` file in the repository root enables the **Cite this
repository** button on GitHub, which generates the citation in APA and
BibTeX formats.

Every TallyHo release is also archived on [Zenodo](https://zenodo.org)
(CERN's archiving service for research) with a **permanent DOI**: version
1.0.0 has the DOI
[10.5281/zenodo.21979207](https://doi.org/10.5281/zenodo.21979207).
The DOI identifies the archived version stably, even if the GitHub link
changed.
