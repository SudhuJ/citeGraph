"""Minimal cached OpenAlex client.

Every response is cached on disk (keyed by the request URL without the API key),
so re-running the pipeline costs no API credits.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
BASE = "https://api.openalex.org"
MAILTO = "sudhanva.joshi@students.iiit.ac.in"


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_env()
_client = httpx.Client(timeout=60, headers={"User-Agent": f"citeGraph (mailto:{MAILTO})"})


def get(path: str, params: dict | None = None) -> dict:
    params = {k: v for k, v in (params or {}).items() if v is not None}
    key_src = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
    f = CACHE / (hashlib.sha1(key_src.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())

    q = dict(params, mailto=MAILTO)
    if api_key := os.environ.get("OPENALEX_API_KEY"):
        q["api_key"] = api_key
    for attempt in range(6):
        r = _client.get(BASE + path, params=q)
        if r.status_code == 200:
            break
        if r.status_code in (429, 500, 502, 503, 504):
            wait = min(int(r.headers.get("retry-after", 0) or 0) or 2**attempt, 60)
            print(f"  [oa] {r.status_code} on {path}, retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"OpenAlex {r.status_code}: {r.text[:300]}")
    else:
        raise RuntimeError(f"OpenAlex gave up after retries: {key_src}")

    remaining = r.headers.get("x-ratelimit-remaining")
    if remaining is not None and int(remaining) < 200:
        print(f"  [oa] warning: only {remaining} credits left today", file=sys.stderr)
    data = r.json()
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data))
    return data


def paginate(path: str, params: dict, max_pages: int | None = None):
    """Cursor-paginate a list endpoint, yielding results."""
    cursor, pages = "*", 0
    while cursor:
        data = get(path, dict(params, cursor=cursor, **{"per-page": 200}))
        yield from data["results"]
        cursor = data["meta"].get("next_cursor")
        pages += 1
        if max_pages and pages >= max_pages:
            return


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def short(oa_id: str | None) -> str | None:
    """'https://openalex.org/W123' -> 'W123'."""
    return oa_id.rsplit("/", 1)[-1] if oa_id else None
