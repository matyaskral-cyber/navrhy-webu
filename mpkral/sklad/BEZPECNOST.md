# Zabezpečení skladu — postup nasazení

Dřív web skladu ověřoval heslo jen v prohlížeči a databáze byla otevřená
komukoli s veřejným klíčem (šlo číst, přepsat i smazat celý sklad).
Teď: přihlášení přes Supabase Auth + RLS v databázi.

**Pořadí je důležité, jinak web/sync na chvíli přestane fungovat.**

1. **Uživatelé** — Supabase → Authentication → Users → *Add user* → *Create new user*,
   e-mail + silné heslo, zaškrtnout *Auto Confirm User*. Pro Petra a pro „propom“.
2. **Admin** — v SQL Editoru spustit (s Petrovým e-mailem):
   ```sql
   update auth.users
     set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"sklad_role":"admin"}'
     where email = 'PETR@EMAIL.CZ';
   ```
3. **Secret klíč pro sync** — Supabase → Project Settings → API Keys → Secret keys → vytvořit.
   Na počítači, kde běží `SYNC_SKLAD.bat`, uložit do souboru `supabase_secret.txt`
   vedle skriptů (jen klíč, jeden řádek). Soubor je v `.gitignore` — **nikdy ho necommitovat**.
4. **Nasadit tuhle verzi webu a skriptů** (merge do main → GitHub Pages).
   Otestovat přihlášení e-mailem a jeden běh `SYNC_SKLAD.bat`.
5. **Zamknout databázi** — v SQL Editoru spustit `supabase_rls.sql`.
   Ověřit, že web po přihlášení data pořád vidí.
