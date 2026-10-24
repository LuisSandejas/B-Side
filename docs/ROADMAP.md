# Roadmap

## Now

- [x] Single-file browser game: Daily Set and Endless modes, seven modifiers
- [x] Procedural pixel art, genre-themed arenas, rarity effects
- [x] Live-generated, reactive music
- [x] Song catalog table in Supabase, with the built-in list as an offline fallback
- [x] Deploy on Vercel with auto-deploys from GitHub
- [x] Home screen, daily missions, Spotlight, score curve and share card
- [x] ~2,700-song catalog with rarity tiers and "name an artist" cards
- [ ] Push the database migrations (`supabase db push`) so real scores feed the curve
- [ ] Share with friends for playtesting

## Next: a much bigger catalog

Goal: tens of thousands of well-known songs, so almost anything a player types is recognized.

1. **Catalog pipeline** — a script that builds the catalog from [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_Database) data (titles, artists, release years, genre tags), keeps songs above a popularity cut, maps them onto the seven genres, and loads them into Supabase.
2. **Popularity** — the hardest field to source. Options, in order of simplicity: hand/estimated scores during the build; Last.fm listener counts (commercial use requires permission from Last.fm); other providers after checking their terms. Spotify's API is not an option for new apps (popularity was removed and access is capped).
3. **Server-side search** — once the catalog is too big to download on every visit, move autocomplete and song matching to a Supabase function backed by the trigram indexes that already exist on `title` and `artist`.

## Then: playing together

- Shared **Daily leaderboard** and **Endless high scores** (a `scores` table plus a function that sanity-checks submissions)
- Nicknames without sign-up
- A share link that previews nicely in group chats
- Basic analytics to see where new players get stuck

## Later

- Custom domain (`.io` costs roughly $35–80 a year depending on the registrar; compare renewal prices, not just the first year)
- Player accounts that sync rank, crate and streaks across devices
- Weekly special bosses
- Your own original tracks as rare collectibles

## Before monetizing

Have a lawyer review: the terms of whichever music-data sources the catalog uses, and how artist names appear in the game and in marketing.
