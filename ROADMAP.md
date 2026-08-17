# Roadmap — implementazioni future

Priorità: **P1** (alto impatto / costo basso) · **P2** (medio) · **P3** (basso
impatto o dipende da fattori esterni).

Legenda stato: `[x]` fatto · `[~]` in corso · `[ ]` da fare

## P1 — Migliorie rapide

- [x] **affluenza_pct nel CSV**: il campo usciva vuoto (es. riga Roma 2021).
      Risolto: fallback `votanti / elettori * 100` quando il sito non
      espone la percentuale (commit 5b56365, 83000e3). Verificato dal vivo
      su Roma 12/02/2023 (37.2%).
- [~] **CI attivo**: workflow pronto e versionato in
      `.github/workflows/ci.yml` (matrix Python 3.9-3.12,
      `pytest -m "not integration"` + `ruff check`). Resta da autorizzare lo
      scope `workflow` sul token di pubblicazione: se il push del file sotto
      `.github/workflows` fallisce con 403, serve `gh auth refresh -s
      workflow` e poi il push.
- [x] **Test di integrazione** (rete, opzionali): fatto — `tests/test_integrazione.py`
      marcato `@pytest.mark.integration`, escluso dal default con
      `addopts="-m 'not integration'"` (commit 83000e3). Esteso a 5 tipi di
      elezione (G/R/F/E/P): `leggi_date` per tutti + estrazione reale di una
      data su comunali (ROMA) e referendum (AFFILE, 5 quesiti). Da eseguire
      su schedule nel CI quando riattivato.

## P2 — Ottimizzazioni

- [~] **Catena condivisa tra comuni**: oggi per ogni comune si rifà la
      sequenza data → area → regione (identica per tutti). Ristrutturare
      `trova_comune` per eseguire una sola volta la parte comune per data e
      scendere poi per provincia/comune: ~3x meno richieste con 3 comuni,
      molto di più con liste lunghe. *(programmato: cronjob 01/09)*
- [ ] **Retry con backoff**: su errori di rete/HTTP 5xx, riprovare con
      attesa esponenziale (es. 2, 4, 8 s) prima di segnare `ERRORE` — il
      sito è un archivio ministeriale con picchi di traffico.
- [x] **Cache dei form decodificati**: fatta — `CachedSession` con SQLite
      in `~/.cache/tallyho/cache.db` (commit e185305), opzioni `--no-cache`
      e `--cache-ttl`. Verificata dal vivo: 0% → 100% di richieste servite
      da cache al secondo run.

## P3 — Robustezza e documentazione

- [ ] **Tolleranza ai cambi del sito**: monitorare la struttura del form
      (presenza dei `sel_sezione*`, formato delle option) e, se cambia,
      fallire con un messaggio chiaro che indica cosa cercare, invece di
      un generico "non votato". Idea: uno snapshot di riferimento dei
      selettori da confrontare a ogni run.
- [x] **README in inglese**: fatto — `README.en.md` (traduzione completa con
      pitch, funzionalità, installazione, uso, opzioni, formato output,
      citazione e DOI), link dal README principale, sezione "Contributing"
      in italiano e in inglese.
- [ ] **Politiche per comune**: il sito pubblica il voto per collegio, non
      per comune (limite della fonte). Valutare se aggregare i dati per
      comune via open data DAIT (scrutini per sezione, se pubblicati) —
      solo come ricerca, senza promettere funzionalità.
- [x] **Archiviazione Zenodo + DOI**: fatto — repo collegato a Zenodo,
      release v1.0.0 archiviata, DOI 10.5281/zenodo.21979207 in
      `CITATION.cff` e README (commits 8e3845c, f033021).

## P4 — Dataset builder e scala territoriale

- [ ] **Dataset builder `--provincia X` / `--tutti-comuni`**: estrazione
      bulk di tutti i comuni di una provincia/regione. È il salto da "un
      comune" a "un territorio". Prerequisito: catena condivisa (P2) per
      non fare decine di migliaia di richieste.
- [ ] **Aggregazione serie storiche provincia/regione** (`tallyho-aggrega`):
      somma voti e affluenza aggregata per livello territoriale. Elaborazione
      locale, nessun rischio.

## P5 — Analytics e integrazioni dati

- [ ] **Delta/swing tra elezioni consecutive**: variazione % per lista,
      indice di volatilità elettorale di Pedersen. Punto delicato: matching
      dei nomi partito tra date storiche.
- [ ] **Join ISTAT popolazione**: dataset popolazione per comune per
      affluenza normalizzata e analisi demografiche del voto (fonte esterna).
- [ ] **Clustering comuni per comportamento di voto** (scikit-learn):
      utile per segmentazione territoriale; dipende dall'aggregazione.
- [ ] **Export GIS (GeoJSON/Shapefile)**: mappe del voto con geometrie
      ISTAT; alto valore per il data journalism, ultimo per complessità.

## P6 — Agenti e distribuzione

- [ ] **Report Markdown per comune**: sintesi leggibile (affluenza, sindaci
      succedutisi, serie) pronta per knowledge base e agenti LLM.
- [ ] **API locale FastAPI**: servire i dataset estratti su HTTP.
- [ ] **Pubblicazione PyPI** (`pip install tallyho`): packaging già pronto,
      serve account PyPI e workflow di release.
- [ ] **Grafici serie storiche** (matplotlib/altair): affluenza e voti nel
      tempo.
- [ ] **CLI completions** (argcomplete): completamento tab per le shell.
