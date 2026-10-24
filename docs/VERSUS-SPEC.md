# B-SIDE Versus: design spec

Replaces the current 1v1 and supersedes `1V1-MODE.md`. Networking is unchanged: the host simulates and broadcasts 5 snapshots/sec over Supabase Realtime, and the guest sends inputs.

**Pitch:** one prompt at a time, rapid fire. The first fitting song summons that musician, who marches on the rival's stage. Famous artists can be stolen with a deeper cut. A match takes about 4 minutes.

## 1. Core loop

- One prompt is live at a time, drawn from `makeRequest()` with a shared seed, so both clients already know prompt n+1.
- **The first correct answer wins the prompt, and the next prompt appears in the same frame.** No grace window. The old card flies to the winner's side while the new one is already typeable.
- The loser keeps their typed text. When they submit it, it is checked against the new prompt.
- If nobody answers in 10 s, the prompt flips with a hint and `sfxAlarm` plays. There is no penalty.
- Each song can be used once per match.
- The host sends `win`, `steal` and `skip` as instant events, separate from snapshots, so the guest's prompt switch never waits for a snapshot.

**A won prompt summons a unit.** `humanSprite(song)` drops onto your stage and walks toward the rival, firing on the beat (`onBeat`) at the nearest enemy unit in its lane.
- **Lane:** auto-picked, so there is nothing extra to input: the lane with the most enemy HP, ties go to the middle.
- **Strength:** `calcStrike` energy base × rarity. Airplay ×1, Fan Favorite ×1.25, Crate Dig ×1.6, White Label ×2.
- **Counter ring:** a unit deals ×1.5 to the genre it beats, with a "COUNTER!" pop.
- **Stage hit:** a unit that reaches the enemy stage deals its remaining HP as crowd damage, then is gone.
- **Combo:** 3 prompts in a row makes your next unit a **Headliner** (1.5× size and power, gold outline). The combo resets when the rival wins a prompt.
- **Kill streaks:** `STREAK ×n` pops and the climbing `sfxKill`, as in the main game.

## 2. Arena: horizontal everywhere

**Decision:** a 288×144 logical canvas (2:1), with nearest-neighbour scaling like `#arena`.
- **Desktop:** scaled up to 4×, with the guess feeds in the side gutters.
- **Phone portrait:** fills the width (about 390×195). The stack is HUD 44 + prompt 56 + arena 195 + feed 72 + input 52, about 420 px, which fits above an open keyboard.
- **Why not vertical:** a tall runway gets buried under the keyboard and reads as "stubby". Left-vs-right reads like a fighting game, even in a screenshot.

Each player sees themselves on the left; the guest's view is mirrored.

| Zone | Reused art |
|---|---|
| Top (y 0–56) | `buildBackground()` skyline. The Topline UFO (`drawShip`) hovers centre as MC and beams each prompt down; on a win the beam swings to the winner. |
| Edges (40 px each) | Stages drawn with `drawBooth` (DJ + turntables facing inward), speakers in team colour: you `#3fe0ff`, rival `#ff5a4f`. |
| Middle (y 64–128) | Three lanes as rows. Sprites flip to face travel, with a team outline (`outlineGrid`) and a coloured shadow. |
| Bottom | `drawCrowd`, split in half. Each half glows with its player's lead. |
| Overlay | `drawMood` stage lights. The round genre sets mood, groove and lights: round 1 random, round 2 the genre that counters the round-1 winner's most played genre, Encore in gold. |

Tags, HP and pops are DOM overlays (`updateLabels()` style), so they stay crisp at any scale.

## 3. The steal

- **Named units:** every 3rd prompt is a **Headline prompt** (gold border, spinning record). Its unit wears a tag in the named-Echo style, `QUEEN · 88`, showing the summoning song's popularity. Named units have 1.5× strength and fire their `genreSkill` if they reach a stage.
- **Rule:** while a named unit is on the field, its opponent steals it by submitting any song by that artist **with popularity lower than the tag**.
  - It goes in the same input box, and steal checks run before prompt checks.
  - If one song steals and also answers the prompt, that is a **DOUBLE PLAY**.
- **Effect:** the unit swaps colour, turns around in place, heals 25%, and its tag drops to the new number. The artist's genre skill hits the victim's units, with its skill sound over ducked music.
- **Limits:** 3 steals per unit, and each steal must go lower than the last. No steals during the 1 s spawn drop.
- **Drama:**
  - 140 ms hit-stop.
  - `bigStamp` with a disc in the thief's colour: "STOLEN!", then "STOLEN BACK!", then "HEIST!".
  - The feed shows both numbers, e.g. "Bicycle Race 41 < Bohemian Rhapsody 88", which teaches players the popularity scale.

## 4. Guess feed

- Both players' submissions appear, newest on top, 6 per side:
  - Correct: title, artist and rarity chip.
  - Steals: gold.
  - Wrong but real songs: struck through with a reason ("not 90s"). These are funny and show effort.
  - Unrecognised text: shown as `???`, so no free text ever crosses the wire.
- **Desktop:** your column sits left of the arena and theirs on the right.
- **Phone:** a 2-column, 3-row ticker under the arena, in 13 px type.

## 5. Match structure

- **Crowd:** each stage has 100 Crowd.
- **Rounds:** 75 s. A round is won by emptying the rival's crowd, or by having more crowd at the buzzer.
- **Final Chorus (last 20 s):** a stamp, units walk 1.5× faster, `tempoMult` goes up a tier and `sfxRiser` plays.
- **Best of 3,** with a 5 s recap and a "3-2-1 DROP!" countdown between rounds.
- **Encore (sudden death):** triggers if a round ends within 5 crowd, or if the match would otherwise tie.
  - Both crowds drop to 1 and units walk at 2×.
  - The first unit to touch a stage wins, so stealing is the only defence.
  - If 30 s pass with no hit, the higher score wins.
- **Target:** 3–4.5 min, about 50–70 prompts.

## 6. Juice map (existing effects)

| Moment | Effect |
|---|---|
| Prompt won | `sfxCorrect` in key, era callout (`calloutFor`), dust burst on unit drop, light shake |
| Rare song | `rarityFX` as in the main game. Crate Dig: stamp + 160 ms hit-stop. White Label: "THAT'S A B-SIDE!" with disc, rays and 420 ms hit-stop |
| Counter / kill | "COUNTER!" pop, `sfxHit`, streak pops |
| Stage hit | `sfxBreach`; shake on the victim's screen only; crowd bar flash |
| Steal | §3, plus `sfxReclaim` and the genre skill sound |
| Headliner | `sfxCombo`, gold outline |
| Final Chorus / Encore | `sfxRiser`, then `sfxDrop`, white flash, "TEMPO UP!" |
| Round / match end | `sfxFanfare` / `sfxWin`; `sfxLose` for the loser |

`prefers-reduced-motion` turns off shake and hit-stop.

## 7. Sound

- The main soundtrack keeps playing from lobby to result, with no silent screens.
- The round genre picks the groove.
- `momentum()` becomes your crowd lead, so the music brightens when you're ahead.
- `tempoMult` rises with the prompt rate and steps up at Final Chorus. Encore plays at the 192 bpm cap.
- SFX stay in the song's key, and skills duck the music.
- The rival's wins play a softer, lower `sfxRight`.

## 8. Lobby

- **Username:** asked once and kept in the profile.
  - 2–12 characters: letters, digits, space, `_` and `-`.
  - Trimmed, with repeated spaces collapsed.
  - Checked against a built-in blocklist after leetspeak normalisation.
  - Prefilled with a generated name such as "CrateDigger42".
- **Private room:**
  - A 5-letter code with no O/0/I/1, and the link `/?vs=KX7QP`.
  - **Invite** uses `navigator.share`, falling back to copy: "Think you know more songs than me? B-SIDE Versus: <link>".
  - Opening the link goes to the name prompt, then straight into the room.
- **Random:** 15 s in the queue with a spinning-vinyl loader, then bot fallback. The bot is labelled "BOT".
- **Bots** use real answers through `answers()`/`requestHint()`:

| Level | Answer time | Wrong rate | Songs | Steals |
|---|---|---|---|---|
| Opener | 6–9 s | 15% | Airplay only | Never |
| Headliner | 3.5–6 s | 8% | Mixed | 30% of chances |
| Legend | 2–3.5 s | 3% | Leans rare | 70%, and re-steals |

- **VS splash (2 s):** both names, device icons and the head-to-head record.

## 9. Winner card

**The image:** 1080×1350 in `makeShareCard` style.
- The B-SIDE logo with a VERSUS ribbon.
- **"LUIS def. MARCO 2–1"** with round pips.
- Per player: persona (`personaOf`, falling back to "Rookie"), songs, steals, fastest answer.
- **Rarest song of the match:** with its rarity badge.
- **Best steal.**
- The challenge link.

**Copy text** (spoiler-free, Wordle-style):

```
B-SIDE VERSUS  LUIS 2-1 MARCO
<one emoji per prompt: blue square = Luis, red square = Marco, star = steal; 10 per line>
Rarest: "Svefn-g-englar" (White Label)
Best steal: Queen, Bicycle Race (41)
Beat me: b-side-murex.vercel.app/?vs=KX7QP
```

## 10. Viral hooks

- **Rematch:** when both players press it, a 3 s countdown starts in the same room.
- **Head-to-head record** per pair ("LUIS 3–2 MARCO"), shown on the splash and the card.
- **"Challenge a friend"** on the main-game result screen opens a private room.
- The room code stays in the URL, so a refresh rejoins the room.

## 11. Anti-frustration

- **Simultaneous answers:** the host holds its own submissions for RTT/2, with RTT pinged every 2 s. Two correct answers within 60 ms are a **PHOTO FINISH**, and both players summon a unit.
- **Spam guard:** 3 wrong answers in 3 s jams the input for 1 s ("JAMMED").
- **Underdog:** while 30+ crowd behind, your units get +30% HP.
- **Depth vs speed:** rarity multipliers and steals keep a slower, deeper player in the game.
- **Phone vs keyboard:** both get the main game's `renderSuggest` dropdown, which levels the field.

## 12. Remove

- The vertical runway and the `vsDraw` rectangles.
- The 3 s half-unit grace window.
- The `vsFb`/`vsSay` message line.
- "You"/"Opponent" labels.
- The 2:00 clock.
- The `.vs-req` and `.vs-tag` styles; use the main banner and tags instead.
- Underlined text links; use real buttons.
- Bot buttons as a primary lobby option; they move behind "Practice".

## 13. Build list

**P0:**
1. A horizontal 288×144 arena reusing the main game's art and DOM tags.
2. The rapid-fire loop: instant next prompt, instant events, 10 s skip.
3. Units: rarity, counter ring, auto-lane, beat fire, stage damage, Headliner.
4. Named units and the steal, with stamps.
5. The guess feed (desktop gutters, phone ticker).
6. 75 s rounds, Final Chorus, best of 3, Encore.
7. The juice and sound hooks in §6–7.
8. Username, room code and invite link, random queue with bot fallback, 3 bot levels.
9. Winner card, copy text, rematch, head-to-head record.
10. Latency evening, photo finish, spam guard, underdog.
11. The §12 removals.

**P1:**
- A rival "typing…" pulse.
- **Ghost challenge links:** your answers replayed as a bot on the same seed.
- Pairing phones with phones in random matchmaking.
- Spectating through the room link.

---

## Appendix: research notes

- **Clash Royale** (support.clashroyale.com "Elixir"; Wikipedia; Supercell Nov 2019 notes): 3-minute regulation, double elixir in the last minute, then overtime where the first tower wins. Supercell cut matches to 5 minutes for "a more exciting, escalating finish". This gives Final Chorus and Encore.
- **Tetris 99** (Wikipedia; Destructoid): playing well sends attacks at rivals, and badge targeting turns players on the leader to stop snowballing. This gives units-as-attacks and Underdog.
- **Kahoot** (prototypr "Research: In-Game Streaks"; Kahoot forum): points scale with speed, plus a streak bonus. Players valued showing off the streak more than the points, and speed-only scoring is criticised for rewarding guesses. This gives the combo Headliner and rarity weighting alongside speed.
- **Squabble** (Wikipedia; Tom's Guide; PC Gamer): Wordle as a battle royale. HP drains, correct guesses damage rivals and heal you, and wrong guesses hurt, so there is constant pressure and no idle time. This supports the spam guard.
- **Wordle** (Smithsonian; The Spinoff): spread took off with the spoiler-free square grid, which packs the drama of a game into a few lines. This gives the prompt strip in the copy text.
- **skribbl.io / Gartic Phone** (ECML tool inventory; Know Your Meme): free, browser-only, no account, one link to join, any device, played over voice chat. This gives link rooms and username-only identity.
- **SongPop** (Wikipedia): live 1v1 music trivia where the first right pick wins. B-SIDE's point of difference is free recall instead of multiple choice.
- **Mario Kart blue shell** (Game Developer "Rubber banding as a design requirement"; Law of Game Design): comebacks keep races close, but feel unfair when they erase good play. That is why Underdog is a modest +30% HP, not a reset.
- **"Juice it or lose it"** (Jonasson & Purho, 2012; RPG Playground summary): flash, shake, floating text, sound and particles make a flat prototype fun. Shake should signal impact, and particles should stay restrained. This supports the tiered reuse of the main game's effects.
