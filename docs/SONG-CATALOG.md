# Song catalog

The game knows a song only if it's in its catalog: the built-in list inside `index.html`, `data/songs.json`, and any rows in the Supabase `songs` table. Anything else a player types is rejected with a screen shake.

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

## Quality checklist

- Year is the original release year, not a remaster or re-release.
- Title matches how most people write it (the game strips punctuation and "the" when matching, and tolerates small typos).
- Popularity reflects how well known the song is *today*, worldwide.
