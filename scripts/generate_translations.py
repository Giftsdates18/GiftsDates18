#!/usr/bin/env python3
"""Generate worldwide UI translations for GiftsDates.

Reads English source strings (frontend/src/lib/_en_source.json) and the language
list (frontend/src/lib/languages.json), then uses the Emergent LLM key (Gemini
flash) to translate every string into each non-curated language, writing one
JSON file per language into frontend/src/lib/locales/.

Resumable: already-translated keys are reused; only missing keys are requested.
"""
import os, json, asyncio, re, sys, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage

LIB = Path("/app/frontend/src/lib")
LOCALES = LIB / "locales"
LOCALES.mkdir(exist_ok=True)
EN = json.loads((LIB / "_en_source.json").read_text(encoding="utf-8"))
LANGS = json.loads((LIB / "languages.json").read_text(encoding="utf-8"))
KEY = os.environ["EMERGENT_LLM_KEY"]

# Languages that already have high-quality curated inline translations in i18n.js
CURATED = {"en", "ru", "es", "fr", "de", "pt", "zh", "hi", "bn", "ur", "ar"}
CHUNK = 140
CONCURRENCY = 4

ALL_KEYS = list(EN.keys())


def parse_json(text):
    if not isinstance(text, str):
        text = str(text)
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1:
        t = t[s:e + 1]
    return json.loads(t)


async def translate_chunk(lang_code, english_name, keys, attempt=1):
    sys_msg = (
        f"You are a professional UI localizer. Translate the VALUES of the given JSON "
        f"object from English into {english_name}. Return ONLY a valid JSON object with "
        f"the EXACT same keys and translated string values, nothing else.\n"
        f"Rules:\n"
        f"- Keep placeholders like {{n}}, {{o}}, {{d}}, {{t}}, {{s}} EXACTLY unchanged.\n"
        f"- Keep emojis and currency amounts (e.g. $49.99) unchanged.\n"
        f"- Do NOT translate the brand name 'GiftsDates'. Keep 'VIP' and 'Premium' as-is.\n"
        f"- Preserve any markup/symbols and line breaks.\n"
        f"- Keep it natural and concise for a dating-app interface."
    )
    payload = json.dumps({k: EN[k] for k in keys}, ensure_ascii=False)
    chat = LlmChat(
        api_key=KEY, session_id=f"tr-{lang_code}-{attempt}-{keys[0]}",
        system_message=sys_msg,
    ).with_model("gemini", "gemini-3-flash-preview")
    resp = await chat.send_message(UserMessage(text=payload))
    try:
        obj = parse_json(resp)
    except Exception:
        if attempt < 3:
            await asyncio.sleep(2)
            return await translate_chunk(lang_code, english_name, keys, attempt + 1)
        raise
    return {k: obj.get(k, EN[k]) for k in keys}


async def do_language(lang, sem):
    code = lang["code"]
    if code in CURATED:
        return
    out_path = LOCALES / f"{code}.json"
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    missing = [k for k in ALL_KEYS if k not in existing or existing.get(k) in (None, "")]
    if not missing:
        print(f"[skip] {code} complete ({len(existing)} keys)", flush=True)
        return
    chunks = [missing[i:i + CHUNK] for i in range(0, len(missing), CHUNK)]
    print(f"[start] {code} ({lang['englishName']}) — {len(missing)} missing in {len(chunks)} chunks", flush=True)

    async def run_chunk(ck):
        async with sem:
            try:
                return await translate_chunk(code, lang["englishName"], ck)
            except Exception as ex:
                print(f"[err] {code} chunk failed: {ex}", flush=True)
                return {k: EN[k] for k in ck}

    results = await asyncio.gather(*[run_chunk(c) for c in chunks])
    for r in results:
        existing.update(r)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out_path)
    print(f"[done] {code} — {len(existing)} keys written", flush=True)


async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    targets = [l for l in LANGS if l["code"] not in CURATED]
    print(f"Translating {len(ALL_KEYS)} strings into {len(targets)} languages...", flush=True)
    # Process languages one at a time (chunks within a language run concurrently)
    for lang in targets:
        t0 = time.time()
        await do_language(lang, sem)
        print(f"    ({time.time()-t0:.1f}s)", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
