# Roadmap — implementazioni future

Priorità: **P1** (alto impatto / costo basso) · **P2** (medio) · **P3** (basso
impatto o dipende da fattori esterni).

## P1 — Migliorie rapide

- [ ] **affluenza_pct nel CSV**: il campo esce vuoto (es. riga Roma 2021).
      Il sito fornisce la percentuale in pagina; se assente, calcolarla
      come `votanti / elettori * 100` prima dell'export.
- [ ] **CI attivo**: ripristinare `.github/workflows/ci.yml` (già pronto,
      matrix Python 3.9-3.12) — serve `gh auth refresh -s workflow`
      sull'account di pubblicazione, poi push del workflow.
- [ ] **Test di integrazione** (rete, opzionali): estendere i test unitari
      con un test marcato `@pytest.mark.integration` che esegue una singola
      data su un comune noto (es. `--data 03/10/2021 --comuni ROMA`) e
      verifica che il CSV contenga almeno una riga. Da escludere dal CI
      di default (o eseguire su schedule) per non dipendere dal sito.

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

