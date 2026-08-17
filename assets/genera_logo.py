#!/usr/bin/env python3
"""Genera 3 varianti del logo TallyHo: mio->gpt-image-2, qwen->gpt-image-2, qwen->mai-image-2.5-pro."""
import json
import os
import re
import time
import urllib.request

KEY = os.environ.get("OPENROUTER_API_KEY") or open(
    os.path.expanduser("~/.config/openrouter/key")).read().strip()
API = "https://openrouter.ai/api/v1/images/generations"

prompt_mio = open('prompt_logo_mio.txt', encoding='utf-8').read()
qwen_raw = open('prompt_logo_qwen.txt', encoding='utf-8').read()
# estrae il blocco PROMPT FINALE ripulito dai fence di markdown
m = re.search(r'PROMPT FINALE\s*\n+```text\s*\n(.*?)```', qwen_raw, re.S)
prompt_qwen = m.group(1).strip() if m else qwen_raw.split('PROMPT FINALE', 1)[-1].strip()

job = [
    ("logo_mio_gpt", "openai/gpt-image-2", prompt_mio),
    ("logo_qwen_gpt", "openai/gpt-image-2", prompt_qwen),
    ("logo_qwen_mai", "microsoft/mai-image-2.5-pro", prompt_qwen),
]

for nome, modello, prompt in job:
    payload = {
        "model": modello,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "high",
        "background": "auto",
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            resp = json.loads(r.read().decode())
        b64 = resp["data"][0].get("b64_json")
        url = resp["data"][0].get("url")
        import base64
        if b64:
            open(f"{nome}.png", "wb").write(base64.b64decode(b64))
        elif url:
            urllib.request.urlretrieve(url, f"{nome}.png")
        cost = resp.get("usage", {}).get("cost")
        print(f"[OK] {nome} ({modello}) in {time.time()-t0:.0f}s cost=${cost}", flush=True)
    except Exception as e:
        print(f"[ERR] {nome} ({modello}): {e}", flush=True)
print("FINE", flush=True)
