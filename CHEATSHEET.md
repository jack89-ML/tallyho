# TallyHo — Cheatsheet rapido

TallyHo estrae la storia elettorale italiana (dal 1946) dall'Archivio Storico
del Ministero dell'Interno, comune per comune, e la salva in CSV/JSON.
Questa guida è per chi non usa la riga di comando tutti i giorni.

---

## 1. Prerequisiti (una volta sola)

```bash
git clone https://github.com/jack89-ML/tallyho
cd tallyho
python3 -m venv .venv
.venv/bin/pip install -e .
```

Funzionalità extra (opzionali):
```bash
.venv/bin/pip install -e ".[xlsx]"      # export Excel
.venv/bin/pip install -e ".[parquet]"   # export Parquet
.venv/bin/pip install -e ".[all]"       # tutte le extra
```

---

## 2. I comandi essenziali

### Serie storica di un comune (tutte le date disponibili)
```bash
tallyho --comuni ROMA
```
Risultato: `dati_elezioni/elezioni_<data_ora>.csv` e `.json`

### Più comuni insieme
```bash
tallyho --comuni ROMA,MILANO,NAPOLI
```

### Una data specifica (per fare prima)
```bash
tallyho --comuni ROMA --data 03/10/2021
```

### Solo l'ultima tornata (test rapido)
```bash
tallyho --comuni ROMA --solo-ultima-data
```

### Altro tipo di elezione
| Tipo | Elezione        | Esempio                            |
|------|-----------------|------------------------------------|
| G    | Comunali (default) | `tallyho --comuni ROMA`          |
| R    | Regionali       | `tallyho --tipo R --comuni ROMA --nome-regione LAZIO` |
| C    | Camera          | `tallyho --tipo C --comuni ROMA`   |
| S    | Senato          | `tallyho --tipo S --comuni ROMA`   |
| E    | Europee         | `tallyho --tipo E --comuni ROMA`   |
| F    | Referendum      | `tallyho --tipo F --comuni ROMA`   |
| P    | Provinciali     | `tallyho --tipo P --comuni ROMA`   |

### Dove salvare i file
```bash
tallyho --comuni ROMA --out ./dati
```

---

## 3. Come sapere cosa scrivere (--elenca)

Non sai quale regione/provincia usare? Lo chiedi al sito:

```bash
tallyho --elenca date                    # tutte le date
tallyho --elenca regioni --data 14/05/2023
tallyho --elenca province --data 14/05/2023 --nome-regione TOSCANA
tallyho --elenca comuni --data 14/05/2023 --nome-regione TOSCANA --province FIRENZE
```

---

## 4. Formati di output

| Flag        | Cosa produce                          | Serve per                          |
|-------------|---------------------------------------|------------------------------------|
| (default)   | CSV + JSON                            | Excel, fogli di calcolo, analisi   |
| `--long`    | CSV "lungo" (una riga per dato)       | pandas, R, analisi statistiche     |
| `--xlsx`    | File Excel (.xlsx)                    | chi lavora solo con Excel          |
| `--parquet` | File Parquet                          | big data, Python avanzato          |

```bash
# Tutto in una volta:
tallyho --comuni ROMA --data 03/10/2021 --long --xlsx
```

---

## 5. Anagrafe degli amministratori (--dait)

Aggiunge al JSON i sindaci/commissari in carica del comune (da open data
del Ministero):

```bash
tallyho --comuni ROMA --dait auto
```

---

## 6. File di configurazione (--config)

Invece di riscrivere le opzioni ogni volta, crea un file `tallyho.toml`:

```toml
comuni = "ROMA,MILANO"
tipo = "G"
out = "dati"
sleep = 1.5
```

e usalo con:
```bash
tallyho --config tallyho.toml
```

Nota: gli argomenti scritti a riga di comando hanno la precedenza sul file.

---

## 7. Errori che puoi vedere

| Messaggio            | Significato                                        | Cosa fare                      |
|----------------------|----------------------------------------------------|--------------------------------|
| `NON_VOTATO`         | Il comune non ha votato in quella data (mandato in corso, ecc.) | Normale, non è un errore |
| `ERRORE` + dettaglio | Problema di rete o pagina inattesa                 | Riprova, controlla la rete     |
| `Data non nell'elenco` | La data scritta non esiste per quel tipo         | Usa `--elenca date`            |

---

## 8. Regole d'oro

1. Il sito non ha un'API: TallyHo naviga il form ufficiale. Usalo con
   moderazione (non lanciare centinaia di comuni in una notte).
2. Se lanci molti comuni, aumenta la pausa: `--sleep 2`
3. I dati vanno verificati sul sito ufficiale per usi istituzionali.
4. Se usi TallyHo in una ricerca o pubblicazione, cita il progetto
   (vedi sezione "Citazione" del README).
