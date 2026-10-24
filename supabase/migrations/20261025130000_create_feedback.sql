-- Player suggestions from the in-game Creator page.
-- Visitors can only add a row; nobody can read them except the project owner (dashboard / service role).

create table if not exists public.feedback (
  id         bigint generated always as identity primary key,
  message    text not null check (char_length(message) between 3 and 800),
  contact    text check (contact is null or char_length(contact) <= 120),
  created_at timestamptz not null default now()
);

alter table public.feedback enable row level security;
revoke all on public.feedback from anon, authenticated;
grant insert (message, contact) on public.feedback to anon, authenticated;
grant all on public.feedback to service_role;

drop policy if exists "Anyone can send a suggestion" on public.feedback;
create policy "Anyone can send a suggestion" on public.feedback for insert to anon, authenticated with check (true);
