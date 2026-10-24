# Architecture

B-SIDE is a single self-contained `index.html`: HTML for the screens, one `<style>` block, and one script wrapped in an IIFE. There are no dependencies. The two fonts (Chakra Petch for UI, Pixelify Sans for pixel text) are self-hosted in `assets/fonts/` under the SIL Open Font License.

This doc walks through the script in the order it's written.

## 1. Utilities

Small helpers: a string hash, a seedable PRNG (`rng`, mulberry32), `norm` (normalizes titles and artists for matching: strips accents, punctuation and the word "the"), Levenshtein distance for typo tolerance, and a 3×5 pixel font (`ptext`) used for text drawn on the canvas.

## 2. Music data

- `GENRES` — the seven genres with label, color and base tempo.
- `RING` — the counter ring order. `beats(g)` and `weakTo(g)` read it.
- `RARITIES` and `rarityOf(song)` — popularity thresholds to tiers.
- `RAW` — the built-in songs: `[title, artist, genre, year, popularity, energy, mood]`.
- `LOCAL` — `RAW` turned into song objects by `finishSong`, which also gives each song a stable id, a 3-note melodic "hook" and a musical key (both derived from the id hash, so they're the same every time).
- `indexCatalog()` — rebuilds `ARTISTS` (songs grouped by artist, with each artist's "fame" = their most popular song) and `FAMOUS` (artists with fame 80+, the only ones who can appear as Echoes). It runs at startup and again whenever songs are added from the online catalog.

## 3. Modifiers, profile, daily

- `MODS` — the modifiers and their score multipliers.
- Profile — read and written to `localStorage` (`bside-profile-v2`), always inside try/catch so the game works when storage is blocked.
- `dailySpec()` — derives today's seed, modifier and starting boss genre from the date.

## 4. Sprites

Characters, aliens and the ship are drawn procedurally onto small grids (`mkGrid`, `gset`), outlined, and cached as canvases. Each genre has an outfit for humans and an accessory for aliens; skin and hair vary by song id.

## 5. Audio engine

Everything is synthesized with the Web Audio API.

- **Signal chain:** music bus → pause low-pass → compressor → limiter. Harmonic parts also pass through a "pump" gain that ducks on each kick and a tone filter that opens with your combo. A generated plate reverb is fed by per-voice sends.
- **Sequencer:** 16 steps per bar, scheduled ~150 ms ahead on a 25 ms timer (`musicTick`). `newBar` chooses the groove from the Headliner's genre (`STYLE`), the chord from that genre's progression, the tempo (`GENRES[g].tempo × tempoMult()`, which rises with Echo speed), and how many layers play (one per squad member).
- **Instruments:** drums (kick, snare, clap, metallic hats and ride, toms, timpani), chord voices (Rhodes, power chords, supersaw, pluck, pad, strings), basses (808, saw, sub, picked, walking, pizzicato) and leads (arp, bell, guitar, sax, flute).
- **Harmony:** chords are voice-led; bass, leads, counter-melodies, typing sounds and hit sounds all use the current chord's tones, so nothing clashes. `qt()` quantizes sound effects to the next beat subdivision.

## 6. Song lookup and catalog

- `CATALOG` — the Supabase URL and publishable key.
- `loadCatalog()` — pages through `/rest/v1/songs` (1,000 rows per request), adds songs the game doesn't already know, reindexes, and updates the title-screen status. Times out after 6 s and falls back to the built-in list.
- `localMatch(text)` — scores every catalog song against what was typed (exact, prefix, contains, typo distance). `identify(text)` returns the best match above a threshold, or nothing — in which case the entry is rejected with a screen shake.

## 7. Requests

`REQ` holds one generator per request type. Each returns the HTML shown in the banner and a list of criteria (`C.*`), each with a `test(song)`. `makeRequest` picks a type by weight (`reqWeights`, which changes by phase and modifier), skips the last two types used, and only accepts a request that the catalog can actually answer. On the Daily Set each request uses its own seeded random stream so everyone gets the same sequence.

## 8. Game state and loop

- `newGame(opts)` builds the state object `G`.
- `update(dt)` runs on game time: spawns Echoes (`spawnEcho`), moves them, triggers breaches, boss broadcasts, remixes, request timeouts and scheduled events. It pauses during track intermissions.
- `onBeat(bi)` fires on every musical beat: each squad member attacks the front Echo in its lane on alternating beats (`calcLane`).
- `submitSong → evaluate → accept / reject`: an accepted song fills the request (`calcStrike` → boss damage) and/or reclaims matching Echoes, joins the squad (`addToSquad`), and triggers `rarityFX`.
- `checkPhase()` — when a boss bar empties, either ends the Daily (after track 3) or starts the next track via `intermission`.
- `finish(win)` — scores, grade, rank XP, streaks, crate, best endless run, share text.

## 9. Rendering

- **Layout** (`layout`): the canvas fills the window. The 192-pixel-wide street is scaled so everything from the ship to the squad fits between the top of the screen and the typing bar; extra width becomes more city (`buildWorld`), extra height more sky. The request banner hangs under the ship; HUD panels and side rails float over the side buildings, or collapse to the top on narrow screens.
- **Frame** (`frame → render`): sky effects, background, arena mood (`drawMood`), ship, Echoes, squad links, squad, booth, crowd, rarity rings, projectiles and particles in "street space", then rain, color grade, vignette and flashes in screen space.
- **DOM overlays** on top of the canvas: Echo name tags (`updateLabels`), squad tags (pads), damage popups, big rarity stamps.

## 10. UI

Title screen (daily card, endless card with modifier chips, rank, crate, how to play, catalog status), the in-game HUD and typing bar with the suggestion strip (`updateSuggest`), the fraud-check modal, the first-run coach card, and the results screen.
