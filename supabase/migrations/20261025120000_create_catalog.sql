-- The big song catalog: a few hundred thousand songs built from MusicBrainz and
-- ListenBrainz by scripts/catalog/build_catalog.py and loaded by load_catalog.py.
--
-- Browsers never download this table. They call search_catalog(), which answers
-- from a trigram index in a few milliseconds whatever the table size.

create extension if not exists pg_trgm with schema extensions;

create table if not exists public.catalog (
  id          uuid primary key,              -- MusicBrainz recording MBID
  title       text not null,
  artist      text not null,
  genre       text not null check (genre in ('rock', 'electronic', 'hiphop', 'jazz', 'classical', 'pop', 'rnb')),
  year        smallint check (year between 1600 and 2100),
  popularity  smallint not null check (popularity between 0 and 100),
  listeners   integer not null default 0,    -- ListenBrainz listener count when built
  artist_mbid uuid,
  title_norm  text not null,                 -- norm(title), same normalization as index.html
  search      text not null,                 -- norm(title) || ' ' || norm(artist)
  build_id    text not null                  -- which build loaded the row; old builds are pruned after a reload
);

-- One GIN trigram index serves both prefix (LIKE 'q%') and typo-tolerant (<%) lookups.
create index if not exists catalog_search_trgm on public.catalog using gin (search extensions.gin_trgm_ops);
create index if not exists catalog_build on public.catalog (build_id);

-- Least privilege: no direct table access from the browser, only the search function below.
alter table public.catalog enable row level security;
revoke all on public.catalog from anon, authenticated;
grant all on public.catalog to service_role;

create or replace function public.search_catalog(q text, lim integer default 6)
returns table (id uuid, title text, artist text, genre text, year smallint, popularity smallint, score real)
language plpgsql
stable
security definer
set search_path = public, extensions
set pg_trgm.word_similarity_threshold = 0.55
as $$
declare
  -- same as norm() in the game: lowercase, [a-z0-9 ] only (nothing else reaches LIKE), no standalone "the"
  qq text := left(btrim(regexp_replace(regexp_replace(regexp_replace(lower(coalesce(q, '')), '[^a-z0-9]+', ' ', 'g'), '\mthe\M', ' ', 'g'), '\s+', ' ', 'g')), 80);
  n  integer := least(greatest(coalesce(lim, 6), 1), 20);
begin
  if length(qq) < 2 then
    return;
  end if;
  return query
    select c.id, c.title, c.artist, c.genre, c.year, c.popularity,
           (case
              when c.title_norm = qq or c.search = qq then 3.0
              when c.search like qq || ' %' then 2.5   -- the whole title, maybe part of the artist
              when c.search like qq || '%' then 2.0    -- the start of a title
              else word_similarity(qq, c.search)       -- a typo, or words from the middle
            end + c.popularity / 200.0)::real as score
    from public.catalog c
    where c.search like qq || '%'
       or (length(qq) >= 4 and qq <% c.search)
    order by score desc
    limit n;
end;
$$;

revoke all on function public.search_catalog(text, integer) from public;
grant execute on function public.search_catalog(text, integer) to anon, authenticated, service_role;
