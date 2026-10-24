#!/usr/bin/env python3
"""Load build/catalog.csv.gz into the Supabase `catalog` table.

    read -s "SUPABASE_SECRET_KEY?Supabase secret key: "; export SUPABASE_SECRET_KEY
    python3 scripts/catalog/load_catalog.py

The secret key (Project Settings -> API Keys -> Secret keys) is read from the
environment so it never lands in a file, the repo or shell history. Rows are
upserted 2,000 at a time; rows left over from an older build are deleted at the
end, so the game never sees a half-empty table while a reload is running.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_catalog import ROOT, norm  # noqa: E402  (same normalization as the game)

URL = "https://xrfgssobisrfuemvcqvs.supabase.co"
CHUNK = 2000


def call(method: str, path: str, key: str, body=None, prefer: str = "") -> bytes:
    headers = {"apikey": key, "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(6):
        req = urllib.request.Request(URL + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            if e.code in (401, 403):
                sys.exit(f"Supabase refused the key ({e.code}). Use the secret key, not the publishable one. {msg}")
            if e.code == 404:
                sys.exit("No catalog table yet: run supabase/migrations/20261025120000_create_catalog.sql first.")
            if e.code < 500 and e.code != 429:
                sys.exit(f"Supabase error {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2 ** attempt)
    sys.exit("Supabase kept failing; try again in a minute.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "build" / "catalog.csv.gz"))
    args = ap.parse_args()
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not key:
        sys.exit("Set SUPABASE_SECRET_KEY first (see the top of this file).")

    build_id = time.strftime("%Y%m%d%H%M%S")
    with gzip.open(args.file, "rt", encoding="utf-8", newline="") as f:
        rows = [{
            "id": r["id"], "title": r["title"], "artist": r["artist"], "genre": r["genre"],
            "year": int(r["year"]) if r["year"] else None, "popularity": int(r["popularity"]),
            "listeners": int(r["listeners"]), "artist_mbid": r["artist_mbid"] or None,
            "title_norm": norm(r["title"]), "search": f"{norm(r['title'])} {norm(r['artist'])}", "build_id": build_id,
        } for r in csv.DictReader(f)]
    print(f"Uploading {len(rows):,} songs as build {build_id}…")
    t0 = time.time()
    for i in range(0, len(rows), CHUNK):
        call("POST", "/rest/v1/catalog?on_conflict=id", key, rows[i:i + CHUNK], "resolution=merge-duplicates,return=minimal")
        done = min(i + CHUNK, len(rows))
        print(f"\r  {done:,}/{len(rows):,} ({done / (time.time() - t0):,.0f} rows/s)", end="", flush=True)
    print("\nRemoving songs that are no longer in the catalog…")
    call("DELETE", f"/rest/v1/catalog?build_id=neq.{build_id}", key, prefer="return=minimal")
    sample = json.loads(call("POST", "/rest/v1/rpc/search_catalog", key, {"q": "helena", "lim": 3}))
    print("Done. Test search for 'helena':", ", ".join(f"{s['title']} – {s['artist']}" for s in sample) or "no results")


if __name__ == "__main__":
    main()
