# 1v1 mode: design notes

Status: built (bot, private rooms, random matchmaking). The notes below are the design it follows.

## The pitch

Two players face each other across a long runway. Every request either of you answers summons a squad member who walks toward the other player, shooting as usual. Every so often a summoned unit carries an artist's name over its head. Your opponent can **steal** that unit by naming a *less popular* song by the same artist, and you can steal it back the same way. It tests speed and deep music knowledge at once.

## What it borrows from games people already love

| Game | What works there | What B-SIDE 1v1 takes from it |
|---|---|---|
| Clash Royale | short matches (~3 min), lanes, overtime, "sudden death" | a 3-minute round, a base to protect, overtime when tied |
| Tetris 99 / Tetris Battle | doing well *sends attacks* to the other player | answering a request sends a unit at your opponent |
| Typeracer / Nitro Type | real-time race, instant matchmaking, private races by link | answer-first races, random matchmaking, room codes |
| Trivia Crack | head-to-head trivia with a "challenge" to steal progress | the artist steal |
| skribbl.io / Gartic Phone | rooms by short code or link, no sign-up | private rooms with a 5-letter code, no account needed |
| Age of War / tug-of-war games | units meet in the middle and fight | units clash on the runway; stronger one wins |

The mix is unusual (most music games are single-player quizzes), which is good: it's easy to explain as "Clash Royale, but you summon troops by naming songs."

## Fixes to the logistics

1. **The slower player must still be able to act.** If only the first answer counts, the slower player just watches. Fix: both players can answer the same request; the first answer summons a full-strength unit, and anyone who answers within 3 seconds after still summons a weaker one (half HP). Speed matters, but nobody sits idle.
2. **Steals need a clear rule and an end.** Rule: to steal a named unit, play a song by that artist whose popularity is **lower than the song that summoned it**. The unit switches sides and turns around. Each steal makes the next steal harder (it must go lower again), so chains end on their own. Cap: 3 steals per unit, and a 6-second steal window while the unit walks.
3. **Popularity has to be visible and trusted.** Show the summoning song's rarity tier on the unit, and after a steal show both songs' popularity so players learn the scale. The big catalog's listener counts are the source of truth.
4. **Units meeting in the middle.** When two units meet they trade shots; higher remaining HP wins and keeps walking. Rarer songs hit harder, as in the main game.
5. **Win condition.** Each player has a stage with 20 HP. A unit that reaches it does damage equal to its remaining strength. A round lasts up to 3 minutes; if time runs out, lower total damage taken wins.
6. **Best of 3, then sudden death.** Rounds are short, so a match is best of 3. If it's 1-1 after the third round is tied, sudden death: the next unit to reach a stage wins.
7. **Same requests for both players, never repeated songs.** A song played by either player can't be played again that match.
8. **Fairness on mobile.** Typing on a phone is slower than a keyboard, so a match shows each player's device and random matchmaking pairs phones with phones when possible.

## Rooms and matchmaking

- **Private:** "Create room" gives a 5-letter code and a share link (`/play?room=KX7QP`); the friend enters the code or opens the link.
- **Random:** a matchmaking queue pairs whoever has been waiting longest. If nobody is found in ~20 seconds, offer a **bot opponent** so a new game never feels empty. Bots matter a lot while the player base is small.
- **Rematch** button at the end, same room.

## How it would run technically

- **Supabase Realtime** (already in the project) for rooms: presence for who's in the room, broadcast for answers and steals. No new service needed.
- **Host-authoritative:** the room creator's browser runs the simulation and broadcasts the state 10 times a second; the other player sends inputs only. Simple and good enough for friends; a server-checked version (a Supabase Edge Function validating songs with `search_catalog`) can come later if cheating becomes a problem.
- Requests come from a shared seed, like the Daily Set, so both players see the same requests at the same moment.

## Suggested build order

1. Local prototype against a bot (all rules, no networking) to tune pacing and steals.
2. Private rooms with codes over Supabase Realtime.
3. Random matchmaking with bot fallback.
4. Best of 3, sudden death, rematch, share card for the result.
