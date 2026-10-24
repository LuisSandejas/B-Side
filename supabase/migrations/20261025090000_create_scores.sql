-- Anonymous scores for the end-of-set "where you rank" curve.
-- Anyone can submit a score; nobody can read individual rows. The game only sees
-- aggregate numbers through score_stats(), so no player data is exposed.

create table if not exists public.scores (
  id          bigint generated always as identity primary key,
  mode        text not null check (mode in ('daily','endless')),
  day         date,                                   -- the Daily Set's date (null for endless)
  score       integer not null check (score between 0 and 5000000),
  track       smallint not null default 1 check (track between 1 and 500),
  cleared     integer not null default 0 check (cleared between 0 and 100000),
  won         boolean not null default false,
  created_at  timestamptz not null default now()
);

create index if not exists scores_mode_day_idx on public.scores (mode, day);

alter table public.scores enable row level security;

drop policy if exists "Anyone can submit a score" on public.scores;
create policy "Anyone can submit a score"
  on public.scores for insert
  to anon, authenticated
  with check (mode in ('daily','endless') and score between 0 and 5000000);

-- Histogram (24 buckets), total count, max, and how many scores are below p_score.
create or replace function public.score_stats(p_mode text, p_day date default null, p_score integer default null)
returns json
language sql
stable
security definer
set search_path = public
as $$
  with s as (
    select score from public.scores
    where mode = p_mode and (p_day is null or day = p_day)
  ),
  agg as (select count(*) as n, coalesce(max(score), 0) as mx from s),
  b as (
    select width_bucket(score, 0, greatest((select mx from agg), 1) + 1, 24) as k, count(*) as c
    from s group by 1
  )
  select json_build_object(
    'n', (select n from agg),
    'max', (select mx from agg),
    'buckets', coalesce((select json_agg(json_build_array(k, c) order by k) from b), '[]'::json),
    'below', case when p_score is null then null else (select count(*) from s where score < p_score) end
  );
$$;

revoke all on function public.score_stats(text, date, integer) from public;
grant execute on function public.score_stats(text, date, integer) to anon, authenticated;
