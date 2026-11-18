-- M+P Král sklad — zabezpečení tabulky sklad (spustit v Supabase → SQL Editor)
-- Po spuštění:
--   * anonymní přístup (veřejný klíč z webu) nevidí a nemění nic
--   * přihlášený uživatel sklad čte
--   * zapisovat/mazat smí jen uživatel s app_metadata.sklad_role = 'admin'
--   * synchronizační skripty používají secret klíč, ten RLS obchází

alter table public.sklad enable row level security;

-- smaže všechna dosavadní pravidla na tabulce (mohla povolovat přístup anonymům)
do $$
declare p record;
begin
  for p in select policyname from pg_policies where schemaname = 'public' and tablename = 'sklad' loop
    execute format('drop policy %I on public.sklad', p.policyname);
  end loop;
end $$;

revoke all on public.sklad from anon;

create policy sklad_cteni on public.sklad
  for select to authenticated
  using (true);

create policy sklad_zapis_admin on public.sklad
  for all to authenticated
  using ((auth.jwt() -> 'app_metadata' ->> 'sklad_role') = 'admin')
  with check ((auth.jwt() -> 'app_metadata' ->> 'sklad_role') = 'admin');

-- Admin (smí nahrávat Excel z webu) — doplň e-mail Petra:
-- update auth.users
--   set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"sklad_role":"admin"}'
--   where email = 'PETR@EMAIL.CZ';
