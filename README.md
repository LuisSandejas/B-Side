# B-SIDE

A fast music typing game that runs in the browser.

It's 2189. An alien broadcaster called **The Topline** has played nothing but chart hits for so long that the city has forgotten real music. Its **Echoes** — cheap copies of real artists — march down the street toward the last crowd that still remembers. You fight back by typing real songs.

- **Answer the request** the UFO beams down ("a Rock song from the 80s", "finish the title", "unscramble", "name the track"…) to hit the boss.
- **Or type a song by an artist walking toward you** to reclaim that Echo on the spot.
- Every accepted song joins your three-piece **squad**, plays on the beat and fights the Echo in its lane. Rarer songs hit harder and land with a bigger moment.

No build step, no install: the whole game is one `index.html`.

---

## Contents

- [Play locally](#play-locally)
- [Game modes](#game-modes)
- [How it plays](#how-it-plays)
- [Project structure](#project-structure)
- [Song catalog (Supabase)](#song-catalog-supabase)
- [Deploying](#deploying)
- [Development notes](#development-notes)
- [Docs](#docs)

---

## Play locally

Any static file server works. From the repo root:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. A short loading screen gives way to the title screen (a self-playing game in the background); press any key or click to start, which also switches on the audio (browsers block sound until you interact).

---

## Game modes

| Mode | What it is |
|---|---|
| **Daily Set** | One fixed boss fight per day, the same for everyone: same Echo lineup, same boss genre changes, same requests in the same order. Three tracks (boss health bars), then The Topline goes down. Your first run of the day counts toward your score and streak; replays are practice. |
| **Endless** (default) | Tracks keep coming, each a little longer and faster. After track 3 they become *Encore 1, 2, 3…*. The run ends when the crowd's memory hits zero. Your best score, furthest track and Echoes cleared are saved. |

Endless can be played with a **modifier**: Decades Night, No Airplay, Double Time, Wordplay Night, Masquerade, Genre Takeover or No Safety Net. The Daily Set picks one each day (never the two hardest).

**Keeping it fresh.** Every set has a **Spotlight**, a genre or decade that the Echoes and some requests lean toward: the same for everyone on the Daily Set, random on every Endless run. Each day also brings **three daily missions** (for example "Reclaim 5 Echoes" or "Land a Crate Dig"), worth XP, that can be completed in either mode.

**After a set** you see where your score falls on a curve of other players' scores ("You beat 72% of players today"), plus a **result card** image to share. Until enough real scores exist, the curve is an estimate from test plays and says so.

---

## How it plays

**Requests.** Easy ones open each set and harder ones arrive in later tracks:
- *Songs:* genre, decade, "2000 or later", vibe (upbeat, sad, slow, party), love-song titles, songs by a band, by a Grammy winner or by an artist from a given country, era, year window, exact year, title shapes ("a one-word title", "a color in the title"), first letters, songs by a named artist, "a different song by whoever made X", same decade as / older than / newer than a reference song.
- *Name an artist:* a rapper, a pop star, a band, a duo, a British solo artist, an artist from Canada, a Grammy winner, an artist with a one-word name, an artist who had a hit in the 80s, and more. Typing just the artist's name counts; their best-known fitting song joins your squad.
- *Wordplay:* fill in the blank (typing just the missing word counts), unscramble, initials, and name-the-track clue cards.

Single-answer requests are worth ×1.5; two-part requests ×1.4; answering in the first half of the timer ×1.25.

**Rarity.** Every song has a popularity score (0–100) that sets its rarity. The aliens only know the charts, so rarer songs hurt them more:

| Tier | Popularity | Damage | Feel |
|---|---|---|---|
| ○ Airplay | 80+ | ×0.85 | small ring |
| ◐ Fan Favorite | 60–79 | ×1 | ring and a stronger shake |
| ● Crate Dig | 40–59 | ×1.25 | freeze-frame, shockwave, stamp |
| ◆ White Label | under 40 | ×1.5 | long freeze-frame, gold rays, big stamp, choir hit |

When a song lands, a quick scan sweeps over the new squad member before its rarity is revealed.

**Counter ring.** Rock › Electronic › Hip-hop › Jazz › Classical › Pop › R&B › back to Rock. Each genre beats the next one (×1.75) and is weak to the one before (×0.6). ★ Star Echoes only take damage from their counter.

**Squad.** First in, first out, three slots. The middle slot is the **Headliner**: it sets the music's groove, and if its genre counters the boss's broadcast it blocks the boss's attacks. Songs on stage slowly go stale. Songs that share an artist, scene (genre) or decade link up for bonus damage. Click two squad tags to swap them.

**Everything else.** Combos, kill streaks, golden and masked Echoes, a DJ hype meter that builds to a drop, "prove you ain't a fraud" pop quizzes about songs you just played, a rank ladder, and a crate that collects every song you've had accepted.

**Arenas.** The street changes with whatever genre the boss is broadcasting (laser grid for electronic, stage lights and sparks for rock, a disco floor and confetti for pop, and so on), and the sky changes as the set goes on.

**Music.** All music and sound is generated live with the Web Audio API — nothing is sampled. The soundtrack is a chiptune-electro track with a full song structure (intro, verses, a build, a drop) and three rotating melodies, so it takes about five minutes to repeat. Your squad is the band (an empty stage is a bare beat; each member brings in another part), the Headliner's genre restyles the groove, the tempo rises as the Echoes speed up, and combos brighten the mix. Every shot, kill, correct answer and combo has its own 8-bit sound, in the current key and on the beat.

---

## Project structure

```
index.html                    the entire game: markup, styles and script
data/songs.json               the main song catalog (about 2,400 songs; ~300 more are built into index.html)
404.html                      themed "page not found" page
assets/                       social preview image (og.png), app icons, fonts/ (self-hosted, OFL-licensed)
favicon.ico, site.webmanifest browser tab icon and home-screen install info
robots.txt, sitemap.xml       search-engine basics
vercel.json                   security headers and caching for the live site
supabase/
  migrations/
    20261024120000_create_songs.sql   songs table, indexes, read-only access policy
    20261024120100_seed_songs.sql     the songs that ship inside the game
    20261025090000_create_scores.sql  anonymous scores + score_stats() for the end-of-set curve
docs/
  ARCHITECTURE.md             how the game is put together
  SONG-CATALOG.md             catalog schema, rarity rules, adding songs
  ROADMAP.md                  what's next
```

---

## Song catalog and scores (Supabase)

The game knows about 2,700 songs: about 300 built into `index.html` (so it still works if nothing else loads) and the rest in `data/songs.json`, loaded while the splash screen shows. If the Supabase `songs` table has extra rows, those are added on top.

Supabase also stores **anonymous scores** for the end-of-set curve. Anyone can submit a score, but nobody can read individual rows; the game only asks `score_stats()` for a histogram and how many scores sit below yours. Scores are never submitted from `localhost` or from `?autotest` runs, so testing doesn't pollute the data.

The Supabase project URL and **publishable** key are set near the top of the script in `index.html` (`const CATALOG=…`). The publishable key is designed to be public; row-level security only lets visitors read songs and submit scores.

> Never put the database password or a secret/service-role key in `index.html` or anywhere else in this repo.

### First-time setup

Install the [Supabase CLI](https://supabase.com/docs/guides/cli), then from the repo root:

```bash
supabase login
supabase init        # creates supabase/config.toml; keeps the existing migrations
supabase link --project-ref xrfgssobisrfuemvcqvs
supabase db push
```

`supabase init` may ask about editor settings; either answer is fine. `supabase link` asks for the database password — type it into the prompt, don't save it in a file. `supabase db push` creates the `songs` and `scores` tables and seeds the songs. Until then the game still works; the end-of-set curve just stays an estimate.

To add songs, see [docs/SONG-CATALOG.md](docs/SONG-CATALOG.md).

---

## Deploying

It's a static site, so any static host works.

**Vercel (recommended):** in the Vercel dashboard choose **Add New → Project**, import `LuisSandejas/B-Side`, leave the framework preset as **Other** with no build command, and deploy. Every push to `main` redeploys automatically.

**Custom domain:** add it under the project's **Settings → Domains** in Vercel and follow the DNS instructions there. Then replace `https://b-side-murex.vercel.app` with the new domain in `index.html` (canonical and preview-image tags), `robots.txt` and `sitemap.xml`.

**Security headers** (`vercel.json`) include a Content-Security-Policy. If the game ever loads something from a new site (another font host, a new API), add that site to the policy or the browser will block it.

---

## Development notes

- **Test hook.** Open `index.html?autotest` to expose `window.__bside` for scripted play-testing: `step(seconds)` advances the game, `answer()` returns a valid answer to the current request, `state()` returns the live game state, `card()` renders the share card. It also disables the auto-pause when the tab is hidden.
- **Saved data** lives in the browser's `localStorage` under `bside-profile-v2` (rank, XP, streak, daily results, missions, crate, best endless run, whether the first-run tips were shown). That's how the game remembers a returning player: it's per browser and per device, so clearing site data or switching devices starts fresh. Syncing across devices needs player accounts (see the roadmap).
- **Determinism.** The Daily Set seeds every random stream from the date, and gives each Echo spawn, request and boss remix its own seeded stream, so players who play differently still face the same content.

---

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Song catalog](docs/SONG-CATALOG.md)
- [Roadmap](docs/ROADMAP.md)

## License

See [LICENSE](LICENSE).
