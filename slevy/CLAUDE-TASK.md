# Úkol pro Claude Code na Mac Mini

## Co udělat
Postav z existující PWA webové aplikace SlevyDnes mobilní appky pro Android a iOS pomocí Capacitor.

## Kde je projekt
```bash
git clone https://github.com/matyaskral-cyber/navrhy-webu.git
cd navrhy-webu/slevy
```

## Web app (již hotová)
- `index.html` — kompletní single-page PWA aplikace (HTML + CSS + JS v jednom souboru)
- `slevy.json` — data produktů (739 položek, 6 obchodů: Penny, Billa, Lidl, Albert, Kaufland, Tesco)
- `manifest.json` — PWA manifest
- `sw.js` — service worker
- `icons.svg`, `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` — ikony
- `scraper.py` — Python scraper (neřešit, běží přes GitHub Actions)

Web funguje na: https://matyaskral-cyber.github.io/navrhy-webu/slevy/

## Kroky

### 1. Instalace závislostí (pokud chybí)
```bash
brew install node        # Node.js
# Android Studio — stáhnout z https://developer.android.com/studio a nainstalovat
# Xcode — z App Store (pokud ještě není)
```

### 2. Capacitor projekt
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
- `webDir`: `.` (index.html je přímo v slevy/)
- Barva status baru: `#0f1117` (tmavé téma)
- Splash screen: použij icon-512.png

### 4. Android
```bash
npx cap open android
```
- V Android Studio: Build → Generate Signed Bundle / APK
- Vytvořit nový keystore pokud neexistuje
- Release build → APK soubor uložit do `slevy/builds/`

### 5. iOS
```bash
npx cap open ios
```
- V Xcode: nastavit Signing Team
- Bundle ID: `cz.slevydnes.app`
- Product → Archive → Export

### 6. Výsledek
- Android APK v `slevy/builds/slevydnes.apk`
- iOS build v Xcode

## Důležité
- Web dir je `.` (tečka) — všechny soubory webu jsou přímo v `slevy/`
- NEMĚNIT žádné webové soubory (index.html, slevy.json atd.)
- Appka je jen obal kolem existujícího webu
- Tmavé téma: pozadí `#0f1117`, accent `#6c63ff`
- App ikona: `icon-512.png` (gradient fialová→růžová s košíkem)

## Info o projektu
- **Repo:** https://github.com/matyaskral-cyber/navrhy-webu
- **Složka:** `slevy/`
- **GitHub Pages:** https://matyaskral-cyber.github.io/navrhy-webu/slevy/
- **Scraper:** Python, běží denně přes GitHub Actions v 6:00 CET
- **6 obchodů:** Penny (přímý API), Billa (přímý API), Lidl (přímý HTML), Albert (kupi.cz), Kaufland (kupi.cz), Tesco (kupi.cz)
