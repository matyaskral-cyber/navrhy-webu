# Úkol pro Claude Code na Mac Mini

## Co udělat
Postav z existující PWA webové aplikace SlevyDnes mobilní appky pro Android a iOS pomocí Capacitor.

## Kde je projekt
```bash
git clone https://github.com/matyaskral-cyber/navrhy-webu.git
cd navrhy-webu/slevy
```

---

## Co je HOTOVÉ (neměnit!)

### Web aplikace — kompletní PWA
- `index.html` — single-page app (HTML + CSS + JS v jednom souboru), dark theme, 6 obchodů
- `slevy.json` — 739 produktů z 6 obchodů (reálná data, ne mock)
- `manifest.json` — PWA manifest (standalone, PNG + SVG ikony)
- `sw.js` — service worker (stale-while-revalidate, offline podpora)
- `icons.svg`, `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` — ikony appky
- `scraper.py` — Python scraper stahující data z obchodů

### Funkce webu
- Filtrování podle 6 obchodů (Penny, Billa, Lidl, Albert, Kaufland, Tesco)
- Výběr města (60+ českých měst + geolokace)
- Vyhledávání produktů
- Řazení (sleva, cena, název)
- Nákupní košík s odškrtáváním a počítáním ročních úspor
- Instalace z prohlížeče jako PWA (install banner)
- Offline režim

### Scraper — zdroje dat
| Obchod | Zdroj | Metoda | Legální? |
|--------|-------|--------|----------|
| Penny (48 produktů) | penny.cz | JSON API `/api/product-discovery/` | Ano, veřejný API |
| Billa (37) | billa.cz | JSON API `/api/product-discovery/` | Ano, stejná REWE platforma |
| Lidl (78) | lidl.cz | HTML `data-grid-data` atributy | Ano, veřejné stránky, povoleno v robots.txt |
| Albert (163) | kupi.cz | HTML + JSON-LD scraping | Ano, veřejný agregátor |
| Kaufland (107) | kupi.cz | HTML + JSON-LD scraping | Ano |
| Tesco (306) | kupi.cz | HTML + JSON-LD scraping | Ano |

### Auto-update
- GitHub Actions workflow: `.github/workflows/update-slevy.yml`
- Běží denně v 6:00 CET (cron `0 5 * * *`)
- Commituje nový `slevy.json` pokud se data změnila

### GitHub Pages
- Živý web: https://matyaskral-cyber.github.io/navrhy-webu/slevy/
- Repo: https://github.com/matyaskral-cyber/navrhy-webu

---

## Co NEFUNGUJE / co jsme zkusili

### albert.cz — GraphQL API nefunkční
- Albert Online eshop **ukončen 23. 12. 2025**
- GraphQL endpoint `POST https://www.albert.cz/api/v1/` existuje, ale `productSearch` vrací jen 1 produkt
- Dotaz `storeSearch(query: "Praha")` funguje (vrací prodejny), ale produktový katalog je prázdný
- Zkoušeli jsme nastavit store kontext (cookies, headers) — nic nepomohlo
- **Řešení:** kupi.cz jako zdroj pro Albert

### kaufland.cz — blokuje všechny scrapy
- Vrací HTTP 403 na všechny requesty (i s browser User-Agent)
- Cloudflare/bot protection
- Seller API existuje ale vyžaduje seller účet
- **Řešení:** kupi.cz jako zdroj pro Kaufland

### itesco.cz — blokuje všechny scrapy
- Vrací HTTP 403 (Akamai bot protection)
- Vyžaduje JavaScript execution pro přístup
- **Řešení:** kupi.cz jako zdroj pro Tesco

### PWABuilder.com — funguje ale potřeboval PNG ikony
- Původně byly jen SVG ikony → PWABuilder je nepodporoval
- Vyřešeno: vygenerovány PNG ikony (192, 512, apple-touch-icon) přes Python Pillow
- PWABuilder může vygenerovat Android TWA balíček z URL, ale na Mac Mini jdeme přes Capacitor

### cairosvg — nefunguje na tomto Macu
- `pip install cairosvg` se nainstaluje, ale chybí cairo C knihovna (`libcairo.so.2`)
- Nebylo potřeba řešit — PNG ikony vygenerovány přes Pillow

### Capacitor na MacBooku — chyběly nástroje
- Na MacBooku (matyaskral) není Android Studio ani Xcode
- Proto se build přesouvá na Mac Mini

---

## Co ZBÝVÁ udělat (úkol pro tebe)

### 1. Nainstalovat nástroje (pokud chybí)
```bash
# Homebrew (pokud nemáš)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Node.js
brew install node

# Ověř
node -v && npm -v
```
- **Android Studio** — stáhnout ručně z https://developer.android.com/studio a nainstalovat
- **Xcode** — z App Store (~12 GB)

### 2. Vytvořit Capacitor projekt
```bash
cd navrhy-webu/slevy
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init SlevyDnes cz.slevydnes.app --web-dir=.
npm install @capacitor/android @capacitor/ios
npx cap add android
npx cap add ios
npx cap sync
```

### 3. Konfigurace Capacitor (capacitor.config.ts)
- `appId`: `cz.slevydnes.app`
- `appName`: `SlevyDnes`
- `webDir`: `.` (index.html je přímo v slevy/, NE v podsložce)
- Barva status baru: `#0f1117` (tmavé téma)
- Splash screen: použij `icon-512.png`

### 4. Android APK
```bash
npx cap open android
```
V Android Studio:
1. Počkej na Gradle sync
2. Build → Generate Signed Bundle / APK
3. Vyber APK
4. Vytvoř nový keystore (uložit bezpečně!)
5. Release build
6. APK uložit do `slevy/builds/slevydnes.apk`

### 5. iOS
```bash
npx cap open ios
```
V Xcode:
1. Nastav Signing Team (Apple Developer účet potřeba, $99/rok)
2. Bundle ID: `cz.slevydnes.app`
3. Product → Archive → Export

### 6. Výsledek
- Android APK v `slevy/builds/`
- iOS build v Xcode
- Commitnout a pushnout

---

## Důležité poznámky

- **NEMĚNIT webové soubory** (index.html, slevy.json, scraper.py atd.) — jsou hotové a fungují
- Appka je jen **nativní obal** kolem existujícího webu (WebView)
- `webDir` musí být `.` (tečka) — všechny soubory webu jsou přímo v `slevy/`
- Tmavé téma: pozadí `#0f1117`, accent `#6c63ff`, accent2 `#ff6584`
- App ikona: `icon-512.png` (gradient fialová→růžová s nákupním košíkem a %)
- Všechna uživatelská data (košík, město, úspory) jsou v localStorage — privátní per zařízení
- Service worker zajišťuje offline fungování

## Struktura souborů
```
slevy/
├── index.html          ← hlavní web app (vše v jednom souboru)
├── slevy.json           ← 739 produktů (generuje scraper)
├── scraper.py           ← Python scraper (neřešit)
├── manifest.json        ← PWA manifest
├── sw.js                ← service worker v4
├── icons.svg            ← SVG ikona
├── icon-192.png         ← PNG ikona 192×192
├── icon-512.png         ← PNG ikona 512×512
├── apple-touch-icon.png ← Apple ikona 180×180
├── BUILD-APPS.md        ← stručný návod
└── CLAUDE-TASK.md       ← tento soubor
```
