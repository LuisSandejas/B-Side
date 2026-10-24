# Roadmap

## Now

- [x] Single-file browser game: Daily Set and Endless modes, seven modifiers
- [x] Procedural pixel art, genre-themed arenas, rarity effects
- [x] Live-generated, reactive music
- [x] Song catalog table in Supabase, with the built-in list as an offline fallback
- [x] Deploy on Vercel with auto-deploys from GitHub
- [x] Home screen, daily missions, Spotlight, score curve and share card
- [x] ~2,700-song catalog with rarity tiers and "name an artist" cards
- [x] Push the database migrations so real scores feed the curve
- [x] Big catalog from MusicBrainz + ListenBrainz with server-side search
- [x] Indexed search, debounced/cached lookups, offline support
- [ ] Share with friends for playtesting

## Next: catalog polish

- Refresh the big catalog monthly (new releases) with a scheduled job
- Better popularity for genres ListenBrainz under-counts (pop, K-pop, Latin)
- Non-Latin titles (Japanese, Korean, …) with romanized search
- Artist facts (country, band/solo) from MusicBrainz so big-catalog artists work on "name an artist" cards

## Then: playing together

- **1v1 mode**: summon units by answering, steal named units with a less popular song by the same artist, best of 3 (see [1V1-MODE.md](1V1-MODE.md))
- Vercel Web Analytics (one script tag; enable it in the Vercel dashboard first)

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
