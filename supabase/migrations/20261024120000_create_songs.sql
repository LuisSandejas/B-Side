-- Song catalog for B-SIDE.
-- The game ships with a built-in list and adds any extra rows from this table when it loads.
-- Anyone can read songs; only the project owner (dashboard, CLI or service role) can write them.

create extension if not exists pg_trgm with schema extensions;

create table if not exists public.songs (
  id          text primary key,              -- normalized "title artist" key, the same one the game uses
  title       text not null,
  artist      text not null,
  genre       text not null check (genre in ('rock','electronic','hiphop','jazz','classical','pop','rnb')),
  year        smallint check (year between 1000 and 2100),   -- original release year (composition year for classical)
  popularity  smallint not null default 50 check (popularity between 0 and 100),  -- drives rarity: 80+ Airplay, 50+ Fan Favorite, 20+ Crate Dig, below that White Label
  energy      real not null default 0.5 check (energy between 0 and 1),
  mood        real not null default 0.5 check (mood between 0 and 1),           -- 0 = dark or sad, 1 = bright or happy
  source      text not null default 'seed',
  created_at  timestamptz not null default now()
);

-- fuzzy search on titles and artists (for server-side autocomplete later)
create index if not exists songs_title_trgm  on public.songs using gin (title  extensions.gin_trgm_ops);
create index if not exists songs_artist_trgm on public.songs using gin (artist extensions.gin_trgm_ops);
create index if not exists songs_genre_idx   on public.songs (genre);

alter table public.songs enable row level security;

drop policy if exists "Songs are readable by everyone" on public.songs;
create policy "Songs are readable by everyone"
  on public.songs for select
  to anon, authenticated
  using (true);
