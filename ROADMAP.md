# Roadmap — implementazioni future

Priorità: **P1** (alto impatto / costo basso) · **P2** (medio) · **P3** (basso
impatto o dipende da fattori esterni).

## P1 — Migliorie rapide

- [x] **affluenza_pct nel CSV**: il campo usciva vuoto (es. riga Roma 2021).
      Risolto: fallback `votanti / elettori * 100` quando il sito non
      espone la percentuale (commit 5b56365, 83000e3). Verificato dal vivo
      su Roma 12/02/2023 (37.2%).
- [ ] **CI attivo**: ripristinare `.github/workflows/ci.yml` (già pronto,
      matrix Python 3.9-3.12) — serve `gh auth refresh -s workflow`
      sull'account di pubblicazione, poi push del workflow. Il `.gitignore`
      non lo blocca più (riga rimossa in 83000e3); il file ci.yml è
      conservato in /mnt/vault/osint-savelli/analisi/tallyho_archivio/ci.yml.
- [x] **Test di integrazione** (rete, opzionali): fatto — `tests/test_integrazione.py`
      marcato `@pytest.mark.integration`, escluso dal default con
      `addopts="-m 'not integration'"` (commit 83000e3). Da eseguire su
      schedule nel CI quando riattivato.

## P2 — Ottimizzazioni

- [ ] **Catena condivisa tra comuni**: oggi per ogni comune si rifà la
      sequenza data → area → regione (identica per tutti). Ristrutturare
      `trova_comune` per eseguire una sola volta la parte comune per data e
      scendere poi per provincia/comune: ~3x meno richieste con 3 comuni,
      molto di più con liste lunghe.
- [ ] **Retry con backoff**: su errori di rete/HTTP 5xx, riprovare con
      attesa esponenziale (es. 2, 4, 8 s) prima di segnare `ERRORE` — il
      sito è un archivio ministeriale con picchi di traffico.
- [ ] **Cache dei form decodificati**: salvare le `option` decodificate per
      (tipo, data, livello) in `~/.cache/tallyho/` per evitare di riscaricare
      le stesse pagine a ogni run (utile per dataset grandi e per tollerare
      eventuali modifiche temporanee del sito).

## P3 — Robustezza e documentazione

- [ ] **Tolleranza ai cambi del sito**: monitorare la struttura del form
      (presenza dei `sel_sezione*`, formato delle option) e, se cambia,
      fallire con un messaggio chiaro che indica cosa cercare, invece di
      un generico "non votato". Idea: uno snapshot di riferimento dei
      selettori da confrontare a ogni run.
- [ ] **README in inglese**: sezione "Contributing" / README EN per i
      contributori internazionali (il progetto è già pubblicato e
      condiviso su r/osinttools).
- [ ] **Politiche per comune**: il sito pubblica il voto per collegio, non
      per comune (limite della fonte). Valutare se aggregare i dati per
      comune via open data DAIT (scrutini per sezione, se pubblicati) —
      solo come ricerca, senza promettere funzionalità.
- [ ] **Archiviazione Zenodo + DOI**: collegare il repo a Zenodo (servizio
      CERN, gratuito): a ogni release GitHub, Zenodo archivia una snapshot
      e assegna un DOI stabile da citare nelle pubblicazioni. Il file
      `.zenodo.json` con i metadati è già pronto nella radice; manca il
      collegamento account (azione manuale su zenodo.org) e la prima
      release. Dopo: inserire il DOI in `CITATION.cff` e nel README.

