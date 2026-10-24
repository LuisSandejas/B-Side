# Song catalog

The game has two catalogs:

- **The curated list** (about 2,700 songs): the built-in list inside `index.html`, `data/songs.json`, and any rows in the Supabase `songs` table. Echoes, requests and the Daily Set only use these, so they stay recognizable and identical for everyone.
- **The big catalog** (a few hundred thousand songs): the Supabase `catalog` table, searched on the server when a player types something the curated list doesn't know. See [The big catalog](#the-big-catalog) below.

A song in neither is rejected with a screen shake.

`data/songs.json` is an array of `[title, artist, genre, year, popularity, energy, mood]` rows. Years are real release years; popularity, energy and mood are hand estimates.

## Schema

Defined in `supabase/migrations/20261024120000_create_songs.sql`.

| Column | Type | Notes |
|---|---|---|
| `id` | text, primary key | Lowercase `"title artist"` with punctuation and the word "the" removed, e.g. `bohemian rhapsody queen`. |
| `title` | text | As it should be displayed. |
| `artist` | text | Main credited artist. |
| `genre` | text | One of `rock`, `electronic`, `hiphop`, `jazz`, `classical`, `pop`, `rnb`. |
| `year` | smallint | Original release year of the recording (composition year for classical works). |
| `popularity` | smallint 0–100 | How widely known the song is today. Sets rarity (below). |
| `energy` | real 0–1 | Affects base damage. |
| `mood` | real 0–1 | 0 = dark or sad, 1 = bright or happy. |
| `source` | text | Where the row came from (`seed`, `manual`, …). |

Row-level security is on. Anyone can read; only the project owner can write (Supabase dashboard, CLI, or the service-role key on a server — never in the browser).

## Rarity

| Popularity | Tier |
|---|---|
| 80+ | Airplay |
| 60–79 | Fan Favorite |
| 40–59 | Crate Dig |
| under 40 | White Label |

Artists whose most popular song is 80+ can also appear as **Echoes**, so keep those to genuine household names.

## Genre mapping

Map sub-genres onto the seven buckets:

- **rock:** punk, metal, indie, grunge, alternative, emo, folk rock
- **electronic:** house, techno, EDM, dubstep, trance, synthwave, ambient, downtempo
- **hiphop:** rap, trap, drill, grime, chillhop, lo-fi hip-hop
- **rnb:** soul, funk, neo-soul, disco, gospel
- **classical:** orchestral, opera, film score
- **jazz:** swing, bebop, bossa nova
- **pop:** K-pop, dance-pop, synth-pop, country-pop, bedroom pop

## Artist facts

The "name an artist" cards use a small table near the top of the script (`META_RAW`): each artist's home country, whether they're a solo artist, band or duo, and a flag for a competitive Grammy win. Only mark a Grammy win you're sure of. Artists missing from the table still work everywhere else; they just don't count for country, band/duo or Grammy cards.

## Adding songs

**Into the static catalog:** add rows to `data/songs.json` and redeploy (push to `main`).


**One or two songs:** Supabase dashboard → Table Editor → `songs` → Insert row.

**A batch:** write a new migration and push it:

```bash
supabase migration new add_more_songs
# edit the new file in supabase/migrations/, e.g.
#   insert into public.songs (id, title, artist, genre, year, popularity, energy, mood, source) values
#   ('levitating dua lipa', 'Levitating', 'Dua Lipa', 'pop', 2020, 90, 0.82, 0.85, 'manual')
#   on conflict (id) do nothing;
supabase db push
```

**From a spreadsheet:** Table Editor → `songs` → Insert → Import data from CSV, with the column names above as headers.

Duplicates are harmless: the game skips any song it already knows.

## The big catalog

Built from open data by `scripts/catalog/build_catalog.py`:

1. **Songs** come from the [MusicBrainz canonical dump](https://data.metabrainz.org/pub/musicbrainz/canonical_data/), one row per distinct recording (remasters and duplicate releases already merged). The script streams the 7–8 GB CSV straight out of the compressed archive.
2. **Popularity** comes from [ListenBrainz](https://listenbrainz.org) listener counts: artists below a listener cutoff are skipped, and each artist keeps their most-played songs (more for bigger artists).
3. **Cleanup** drops live takes, remixes, remasters, skits, interludes, titles that can't be typed on an English keyboard, and titles with slurs.
4. **Years and genres** come from ListenBrainz metadata (release year, plus recording, album and artist tags mapped onto the seven genres).
5. **The 0–100 popularity score** is fitted against the hand-rated songs in the curated list: `popularity = a + b × log10(listeners)`.

Both sources' data is CC0. ListenBrainz's listeners skew toward rock, indie and electronic fans, so mainstream pop, K-pop and Latin hits can score lower than their real fame.

### Rebuilding and loading

```bash
# 1. download the newest dump (about 2.4 GB) into the cache folder
mkdir -p ~/.cache/b-side-catalog && cd ~/.cache/b-side-catalog
curl -LO https://data.metabrainz.org/pub/musicbrainz/canonical_data/<newest folder>/<file>.tar.zst

# 2. build (about an hour; every API answer is cached, so it resumes if interrupted)
cd ~/Documents/B-Side
python3 scripts/catalog/build_catalog.py        # writes build/catalog.csv.gz (not committed)

# 3. load: paste your secret key at the hidden prompt (Project Settings → API Keys)
read -s "SUPABASE_SECRET_KEY?Supabase secret key: "; export SUPABASE_SECRET_KEY
python3 scripts/catalog/load_catalog.py
```

The loader upserts in batches and deletes rows from older builds only at the end, so the live game never sees a half-empty table. Tune the size with `--min-artist-users` and `--min-song-users`.

**Search:** `search_catalog(q, lim)` normalizes the query again on the server, then uses one GIN trigram index for both prefix matches (`LIKE 'q%'`) and typo-tolerant word similarity (`<%`). Browsers can only call this function; they can't read the table directly.

## Quality checklist

- Year is the original release year, not a remaster or re-release.
- Title matches how most people write it (the game strips punctuation and "the" when matching, and tolerates small typos).
- Popularity reflects how well known the song is *today*, worldwide.
