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
- **Song form:** the soundtrack is one composed chiptune-electro track in a 56-bar form (`FORM`): intro, A, A2, B, a 4-bar break with a filter riser, an 8-bar drop an octave up, C, and B again. Chords come from `CH`, minor progressions in the i–VI–III–VII family. Three melody sets (`MELODIES`) rotate on each pass, so the music runs about five minutes before it repeats exactly. `songTo(section)` jumps to a section (the menu restarts at the intro, a new set at A).
- **Sequencer:** 16 steps per bar, scheduled ~150 ms ahead on a 25 ms timer (`musicTick`). `newBar` takes the groove from the Headliner's genre (`GROOVE`; the title screen uses its own 140 bpm `menu` groove), the tempo (the groove's bpm × `tempoMult()`, rising with Echo speed, capped at 192), and how many layers play (one per squad member). The pulse-wave chip lead always carries the melody.
- **Sound effects:** 8-bit blips and noise crunches (`chip`, `crunch`) in the current key: a "pew" on each squad shot, an explosion plus a ding that climbs with your kill streak, a power-up arpeggio for a filled request, a rarity reveal, combo blips, a coin chime on reclaim, a buzzer on a wrong answer, a charge-up when hype is full, and a fanfare when a track is cleared. Menu sounds (`sfxBlip`, `sfxSelect`, `sfxBack`) go through `uiSfx`, which plays even while the attract demo is running. `qt()` quantizes sound effects to the next beat subdivision.

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

## 10. Front screens

- **Splash** while fonts and `data/songs.json` load (at most ~6 s; the game works with the built-in list if the file is slow).
- **Title screen** (`#startScreen`): the logo and "Press any key to start" on the left, over an attract-mode demo, a real game (`startDemo`, `G.demo`) that plays itself in the background. Demo games never touch the profile, never show quizzes, and keep sound effects, popups and screen flashes off.
- **Main menu** (`#mainMenu`): a classic left-side list (Daily Set, Endless, How to Play, Crate & Rank, Music) navigable with the mouse or arrow keys, with today's missions and streak on the right (`renderTitle`). Endless opens the modifier list (`#modMenu`); Escape goes back. Rank, crate and how-to-play open as sheets. On phones the menu sits at the bottom and the missions at the top.

## 11. Freshness, missions and scores

- `SPOTS` and `G.spot`: each set's Spotlight biases the Echo pool (`echoSpot`) and adds the `spot` and `spotName` request types.
- `MISSIONS`: three per day, picked from the date seed; progress is checked a few times a second during play (`checkMissions`) and stored in the profile.
- `renderDistribution`: draws an estimate curve immediately, submits the score (live site only), then redraws from `score_stats()` once 30+ real scores exist.
- `makeShareCard` / `shareCard`: a 1080×1350 PNG with the score, curve and rarity dots, shared through the system share sheet when available, otherwise downloaded.

## 12. UI

Title screen and side menu (daily, endless with the modifier list, rank, crate, how to play), the in-game HUD and typing bar with the suggestion strip (`updateSuggest`), the fraud-check modal, the first-run coach card, and the results screen.
