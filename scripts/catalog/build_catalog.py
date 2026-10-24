#!/usr/bin/env python3
"""Build B-SIDE's big song catalog from open MusicBrainz and ListenBrainz data.

    python3 scripts/catalog/build_catalog.py

Steps (each one is cached, so an interrupted run picks up where it stopped):

  1. Stream the MusicBrainz canonical dump (one row per distinct recording) and
     collect every credited artist.
  2. Ask ListenBrainz how many people listen to each artist; keep the ones above
     --min-artist-users.
  3. Stream the dump again and collect those artists' songs, dropping live
     takes, remixes, skits, untypeable titles and duplicates.
  4. Ask ListenBrainz how many people play each song; keep each artist's real hits.
  5. Fetch release years and genre tags for the songs that made the cut.
  6. Calibrate a 0-100 popularity score against the hand-rated songs already
     in the game, map tags onto the seven genres, and write build/catalog.csv.gz.

Only the Python standard library and the `zstd` command are needed.
MusicBrainz core data is CC0; ListenBrainz statistics are CC0.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import http.client
import io
import json
import math
import re
import sqlite3
import subprocess
import sys
import tarfile
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path.home() / ".cache" / "b-side-catalog"
DUMP_URL = "https://data.metabrainz.org/pub/musicbrainz/canonical_data/"
LB = "https://api.listenbrainz.org/1/"
UA = "B-Side-catalog/1.0 ( https://github.com/LuisSandejas/B-Side )"
BATCH = 1000  # ListenBrainz's maximum MBIDs per request
WORKERS = 4  # requests in flight

csv.field_size_limit(10_000_000)

# Placeholder artists in MusicBrainz: Various Artists, [unknown], [anonymous], [traditional], [no artist], [data], [dialogue]
SPECIAL_ARTISTS = {
    "89ad4ac3-39f7-470e-963a-56509c546377", "125ec42a-7229-4250-afc5-e057484327fe",
    "f731ccc4-e22a-43af-a747-64213329e088", "9be7f096-97ec-4615-8957-8d40b5dcbc41",
    "eec63d3c-3b81-4ad4-b1e4-7c147d4d2b61", "33cf029c-63b0-41a0-9855-be2a3665fb3b",
    "314e1c25-dde7-4e4d-b2f4-0a7b9f7c56dc",
}

# ---------------------------------------------------------------- text helpers

_COMBINING = re.compile(r"[̀-ͯ]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_THE = re.compile(r"\bthe\b")
_SPACES = re.compile(r"\s+")


def norm(s: str) -> str:
    """Same normalization as norm() in index.html, so server and browser agree on matches."""
    s = _COMBINING.sub("", unicodedata.normalize("NFD", s or "")).lower().replace("&", " and ")
    return _SPACES.sub(" ", _THE.sub(" ", _NON_ALNUM.sub(" ", s))).strip()


# "Song (feat. X)", "Song [with X]", "Song feat. X"
_FEAT = re.compile(r"\s*(?:[\(\[](?:feat|ft|featuring|with)\.?\s[^\)\]]*[\)\]]|\s(?:feat|ft|featuring)\.?\s.*$)", re.I)
# versions that aren't the song people know
_VERSION = re.compile(
    r"[\(\[\-–—/:]\s*[^\)\]]*\b(live|remix|rmx|mix|demo|instrumental|acoustic|edit|version|remaster(?:ed)?|mono|stereo|"
    r"karaoke|a ?cappella|session|rehearsal|take \d|bonus|reprise|commentary|interview|medley|cover|mashup|bootleg|"
    r"sped up|slowed|nightcore|8d|piano|orchestral|unplugged|extended|radio|tv|clean|explicit|dub|vip|rework|flip)\b",
    re.I,
)
_JUNK_TITLE = re.compile(
    r"^(intro|outro|interlude|skit|untitled|hidden track|silence|\[.*\]|track \d+|bonus track)$", re.I
)
# slurs and the words the hand-built list already filters
_BAD = re.compile(r"\b(fuck\w*|nigg\w*|bitch\w*|fag\w*|retard\w*|kike\w*|chink\w*|spic\w*|tranny\w*)\b", re.I)


def clean_title(raw: str) -> str | None:
    t = _FEAT.sub("", raw).strip()
    if not t or len(t) > 70 or _VERSION.search(t) or _JUNK_TITLE.match(t) or _BAD.search(t):
        return None
    if len(norm(t)) < 1:  # nothing typeable on an English keyboard
        return None
    return t


def clean_artist(raw: str) -> str | None:
    a = re.split(r"\s+(?:feat\.?|ft\.?|featuring)\s+", raw, maxsplit=1, flags=re.I)[0].strip()
    return a if a and norm(a) and not _BAD.search(a) else None


# ---------------------------------------------------------------- genres

GENRES = ("rock", "electronic", "hiphop", "jazz", "classical", "pop", "rnb")
# checked in order: more specific tags first ("trip hop" before "hip hop", "dance-pop" before "dance")
GENRE_RULES = [
    ("pop", r"k-?pop|j-?pop|c-?pop|dance-?pop|synth-?pop|electropop|teen pop|bubblegum|bedroom pop|art pop|indie pop|dream pop|hyperpop|latin pop|europop"),
    ("electronic", r"trip.?hop|chillwave|vaporwave|synthwave|downtempo"),
    ("hiphop", r"emo rap|cloud rap|pop rap|country rap"),
    ("rock", r"pop.?punk|pop rock|emo|punk|metal|grunge|rock|shoegaze|post-hardcore|hardcore|indie|alternative|new wave|post-punk|garage|folk|americana"),
    ("hiphop", r"hip.?hop|rap|trap|drill|grime|boom bap|phonk"),
    ("rnb", r"r&b|rnb|rhythm and blues|soul|funk|disco|gospel|motown|blues|reggae|dancehall|afrobeats"),
    ("jazz", r"jazz|swing|bebop|bossa nova|big band|fusion|ragtime"),
    ("classical", r"classical|opera|baroque|orchestral|symphon|chamber|romantic era|film score|soundtrack|video game music|contemporary classical"),
    ("electronic", r"electronic|electro|house|techno|edm|dubstep|trance|drum and bass|dnb|idm|ambient|dance|breakbeat|garage house|uk garage|jungle|hardstyle"),
    ("pop", r"pop|country|latin|reggaeton|singer-songwriter|schlager|ballad|eurovision"),
]
GENRE_RES = [(g, re.compile(rx, re.I)) for g, rx in GENRE_RULES]


def genre_of_tag(tag: str) -> str | None:
    for g, rx in GENRE_RES:
        if rx.search(tag):
            return g
    return None


def vote_genre(tag_groups: list[tuple[list, float]]) -> str | None:
    votes: Counter = Counter()
    for tags, weight in tag_groups:
        for t in tags or []:
            g = genre_of_tag(t.get("tag", ""))
            if g:
                votes[g] += weight * max(1, int(t.get("count") or 1))
    return votes.most_common(1)[0][0] if votes else None


# ---------------------------------------------------------------- ListenBrainz client


class ListenBrainz:
    """Batches MBIDs 1,000 at a time, follows the server's rate-limit headers and caches every answer in SQLite."""

    def __init__(self, cache_path: Path):
        self.db = sqlite3.connect(cache_path)
        self.db.execute("create table if not exists kv (ns text, k text, v text, primary key (ns, k))")
        self.calls = 0
        self.lock = threading.Lock()

    def _post(self, endpoint: str, body: dict) -> list | dict:
        data = json.dumps(body).encode()
        for attempt in range(8):
            req = urllib.request.Request(LB + endpoint, data=data, headers={"User-Agent": UA, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    out = json.load(r)
                    with self.lock:
                        self.calls += 1
                    if int(r.headers.get("X-RateLimit-Remaining", 5)) <= 1:
                        time.sleep(float(r.headers.get("X-RateLimit-Reset-In", 5)) + 0.5)
                    return out
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(float(e.headers.get("X-RateLimit-Reset-In", 10)) + 1)
                elif e.code >= 500:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, json.JSONDecodeError):  # dropped or cut-off responses: retry
                time.sleep(2 ** attempt)
        raise RuntimeError(f"ListenBrainz {endpoint} kept failing")

    def fetch(self, ns: str, ids: list[str], endpoint: str, key: str, extra: dict | None = None, label: str = "") -> dict:
        """Return {mbid: answer} for every id, calling the API only for ids not cached yet."""
        out: dict = {}
        todo = []
        for i in range(0, len(ids), 900):  # SQLite caps bound parameters
            chunk = ids[i:i + 900]
            q = f"select k, v from kv where ns = ? and k in ({','.join('?' * len(chunk))})"
            for k, v in self.db.execute(q, [ns, *chunk]):
                out[k] = json.loads(v)
        todo = [i for i in ids if i not in out]
        chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
        t0, done = time.time(), 0
        # a few requests in flight at once: each takes the server seconds to answer, far below its rate limit
        with ThreadPoolExecutor(WORKERS) as pool:
            futures = {pool.submit(self._post, endpoint, {key: c, **(extra or {})}): c for c in chunks}
            for n, fut in enumerate(as_completed(futures)):
                chunk, res = futures[fut], fut.result()
                rows = res.items() if isinstance(res, dict) else zip(chunk, res)  # popularity answers in order; metadata by mbid
                got = {k: v for k, v in rows}
                for k in chunk:
                    got.setdefault(k, None)
                self.db.executemany("insert or replace into kv values (?, ?, ?)", [(ns, k, json.dumps(v)) for k, v in got.items()])
                self.db.commit()
                out.update(got)
                done += len(chunk)
                if n % 20 == 0 or done == len(todo):
                    rate = done / max(1e-6, time.time() - t0)
                    log(f"  {label}: {done:,}/{len(todo):,} fetched ({rate:,.0f}/s, ~{(len(todo) - done) / max(rate, 1) / 60:.0f} min left)")
        return out


# ---------------------------------------------------------------- dump streaming


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def find_dump(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    found = sorted(CACHE.glob("*.tar.zst"))
    if not found:
        sys.exit(f"No dump found. Download the newest .tar.zst from {DUMP_URL} into {CACHE} or pass --dump.")
    return found[-1]


class _ForwardOnly(io.RawIOBase):
    """Read-only, non-seekable view of a tar member in streaming mode (TextIOWrapper insists on asking)."""

    def __init__(self, f):
        self.f = f

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        data = self.f.read(len(b))
        b[:len(data)] = data
        return len(data)


def stream_rows(dump: Path):
    """Yield (artist_mbids, artist_credit_name, recording_mbid, recording_name) without unpacking the 7 GB CSV to disk."""
    zst = subprocess.Popen(["zstd", "-dc", str(dump)], stdout=subprocess.PIPE, bufsize=1 << 20)
    tar = tarfile.open(fileobj=zst.stdout, mode="r|")  # streaming mode: reads the archive front to back, no seeking
    member = next((m for m in tar if m.name.endswith("canonical_musicbrainz_data.csv")), None)
    if member is None:
        sys.exit(f"{dump} has no canonical_musicbrainz_data.csv")
    text = io.TextIOWrapper(io.BufferedReader(_ForwardOnly(tar.extractfile(member)), 1 << 20), encoding="utf-8", errors="replace", newline="")
    reader = csv.reader(text)
    head = next(reader)
    ix = {name: head.index(name) for name in ("artist_mbids", "artist_credit_name", "recording_mbid", "recording_name")}
    a, c, r, t = ix["artist_mbids"], ix["artist_credit_name"], ix["recording_mbid"], ix["recording_name"]
    n = 0
    for row in reader:
        n += 1
        if n % 5_000_000 == 0:
            log(f"  …{n:,} rows")
        yield row[a], row[c], row[r], row[t]
    tar.close()
    zst.stdout.close()
    zst.wait()


def lead_artist(mbids: str) -> str:
    return mbids.split(",", 1)[0].strip().strip("{}")


# ---------------------------------------------------------------- calibration


def curated_songs() -> dict[tuple[str, str], int]:
    """(norm title, norm artist) -> hand-rated popularity, from index.html's RAW list and data/songs.json."""
    out = {}
    for t, a, _g, _y, pop, *_ in json.loads((ROOT / "data" / "songs.json").read_text()):
        out[(norm(t), norm(a))] = pop
    html = (ROOT / "index.html").read_text()
    raw = html[html.index("const RAW=["):html.index("const LOCAL=")]
    for t, a, pop in re.findall(r"\['((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)','[a-z]+',(?:\d+|null),(\d+),", raw):
        out[(norm(t.replace("\\'", "'")), norm(a.replace("\\'", "'")))] = int(pop)
    return out


# rank in the catalog (0 = most listened) -> 0-100 popularity: top 1% Airplay, next 7% Fan Favorite,
# next 32% Crate Dig, the rest White Label. Hand ratings are almost all hits, so they can't anchor the low end.
POP_BANDS = [(0.0, 95), (0.01, 80), (0.08, 60), (0.40, 40), (1.0, 15)]


def popularity_from_rank(i: int, n: int) -> int:
    q = i / max(n - 1, 1)
    for (q0, p0), (q1, p1) in zip(POP_BANDS, POP_BANDS[1:]):
        if q <= q1:
            return round(p0 + (p1 - p0) * (q - q0) / (q1 - q0))
    return POP_BANDS[-1][1]


def fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


# ---------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", help="path to musicbrainz-canonical-dump-*.tar.zst (default: newest in ~/.cache/b-side-catalog)")
    ap.add_argument("--min-artist-users", type=int, default=500, help="keep artists with at least this many ListenBrainz listeners")
    ap.add_argument("--min-song-users", type=int, default=20, help="keep songs with at least this many listeners")
    ap.add_argument("--max-songs", type=int, default=400_000, help="keep at most this many songs, most played first (fits Supabase's free 500 MB)")
    ap.add_argument("--out", default=str(ROOT / "build" / "catalog.csv.gz"))
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    dump = find_dump(args.dump)
    lb = ListenBrainz(CACHE / "listenbrainz.sqlite")
    log(f"dump: {dump.name}")

    # 1. every credited lead artist
    artists_file = CACHE / f"{dump.stem}.artists.txt"
    if not artists_file.exists():
        log("step 1/6: collecting artists from the dump")
        seen = set()
        for mbids, _credit, _rec, _title in stream_rows(dump):
            seen.add(lead_artist(mbids))
        seen -= SPECIAL_ARTISTS
        artists_file.write_text("\n".join(sorted(seen)))
    all_artists = artists_file.read_text().split()
    log(f"step 1/6: {len(all_artists):,} artists")

    # 2. artist popularity
    log("step 2/6: artist listener counts")
    apop = lb.fetch("artist", all_artists, "popularity/artist", "artist_mbids", label="artists")
    users = {k: (v or {}).get("total_user_count") or 0 for k, v in apop.items()}
    keep_artists = {k for k, u in users.items() if u >= args.min_artist_users}
    log(f"step 2/6: {len(keep_artists):,} artists with {args.min_artist_users}+ listeners")

    # 3. their songs, cleaned and de-duplicated per artist
    log("step 3/6: collecting songs for those artists")
    cand: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)  # (artist mbid, norm title) -> [(recording, title, artist)]
    dropped = Counter()
    for mbids, credit, rec, raw_title in stream_rows(dump):
        lead = lead_artist(mbids)
        if lead not in keep_artists:
            continue
        title, artist = clean_title(raw_title), clean_artist(credit)
        if not title or not artist:
            dropped["title" if not title else "artist"] += 1
            continue
        cand[(lead, norm(title))].append((rec, title, artist))
    log(f"step 3/6: {len(cand):,} candidate songs from {sum(map(len, cand.values())):,} recordings (dropped {dict(dropped)})")

    # 4. song popularity; keep each artist's real hits
    log("step 4/6: song listener counts")
    recs = sorted({r[0] for versions in cand.values() for r in versions})
    rpop = lb.fetch("recording", recs, "popularity/recording", "recording_mbids", label="songs")
    by_artist: dict[str, list] = defaultdict(list)
    for (lead, _nt), versions in cand.items():
        # several recordings can share a title (album, single, duets): the most played one stands for the song
        best = max(versions, key=lambda v: (rpop.get(v[0]) or {}).get("total_user_count") or 0)
        p = rpop.get(best[0]) or {}
        u, listens = p.get("total_user_count") or 0, p.get("total_listen_count") or 0
        if u >= args.min_song_users:
            by_artist[lead].append((u, listens, *best))
    picked = []
    for lead, songs in by_artist.items():
        songs.sort(reverse=True)
        au = max(users.get(lead, 0), 1)
        cap = max(3, min(60, round(6 * math.log10(au) - 6)))  # 150 listeners -> 7 songs, 10k -> 18, 300k -> 27
        top = songs[0][0]
        picked += [(lead, *s) for s in songs[:cap] if s[0] >= top * 0.02]
    if len(picked) > args.max_songs:
        picked.sort(key=lambda p: -p[1])
        log(f"step 4/6: capping {len(picked):,} songs at the {args.max_songs:,} most played (cutoff: {picked[args.max_songs][1]} listeners)")
        picked = picked[:args.max_songs]
    log(f"step 4/6: {len(picked):,} songs from {len({p[0] for p in picked}):,} artists")

    # 5. release years and tags
    log("step 5/6: years and genre tags")
    meta = lb.fetch("meta", [p[3] for p in picked], "metadata/recording/", "recording_mbids", {"inc": "release tag"}, label="metadata")

    # 6. popularity scale, genres, output
    log("step 6/6: calibrating and writing")
    curated = curated_songs()
    rank = {rec: i for i, (_l, _u, _li, rec, _t, _a) in enumerate(sorted(picked, key=lambda p: -p[1]))}

    artist_genre: dict[str, Counter] = defaultdict(Counter)
    rows = []
    for lead, u, listens, rec, title, artist in picked:
        m = meta.get(rec) or {}
        tags = m.get("tag") or {}
        g = vote_genre([(tags.get("recording"), 3), (tags.get("release_group"), 2), (tags.get("artist"), 1)])
        year = (m.get("release") or {}).get("year")
        year = year if isinstance(year, int) and 1600 <= year <= 2030 else None
        pop = popularity_from_rank(rank[rec], len(picked))
        if g:
            artist_genre[lead][g] += 1
        rows.append([rec, title, artist, g, year, pop, u, lead])
    for r in rows:  # songs without tags take their artist's most common genre
        if not r[3]:
            r[3] = (artist_genre[r[7]].most_common(1) or [("pop", 0)])[0][0]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "artist", "genre", "year", "popularity", "listeners", "artist_mbid"])
        w.writerows(sorted(rows, key=lambda r: -r[6]))
    log(f"wrote {len(rows):,} songs to {out} ({out.stat().st_size / 1e6:.1f} MB) in {lb.calls:,} API calls")
    log(f"  genres: {dict(Counter(r[3] for r in rows))}")
    tiers = Counter("Airplay" if r[5] >= 80 else "Fan Favorite" if r[5] >= 60 else "Crate Dig" if r[5] >= 40 else "White Label" for r in rows)
    log(f"  rarity: {dict(tiers)}")


if __name__ == "__main__":
    main()
