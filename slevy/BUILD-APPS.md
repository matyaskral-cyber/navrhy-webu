# SlevyDnes — Sestavení mobilních appek

## 1. Příprava na Mac Mini

```bash
# Stáhni repo
cd ~/Desktop
git clone https://github.com/matyaskral-cyber/navrhy-webu.git
cd navrhy-webu/slevy
```

## 2. Instalace nástrojů

```bash
# Node.js (pokud nemáš)
brew install node

# Ověř
node -v && npm -v

# Xcode — z App Store (pro iOS)
# Android Studio — stáhni z https://developer.android.com/studio
```

## 3. Capacitor projekt

```bash
cd ~/Desktop/navrhy-webu/slevy

# Inicializace
npm init -y
npm install @capacitor/core @capacitor/cli

# Vytvoř Capacitor projekt
npx cap init SlevyDnes cz.slevydnes.app --web-dir=.

# Přidej platformy
npm install @capacitor/android @capacitor/ios
npx cap add android
npx cap add ios

# Synchronizuj web do nativních projektů
npx cap sync
```

## 4. Android APK

```bash
# Otevři v Android Studio
npx cap open android

# V Android Studio:
# 1. Počkej na Gradle sync
# 2. Build → Generate Signed Bundle / APK
# 3. Vyber APK
# 4. Vytvoř nový keystore (nebo použi existující)
# 5. Release build → hotový APK
```

## 5. iOS IPA

```bash
# Otevři v Xcode
npx cap open ios

# V Xcode:
# 1. Vyber svůj Apple Developer tým (Signing & Capabilities)
# 2. Změň Bundle Identifier na cz.slevydnes.app
# 3. Product → Archive
# 4. Distribute App → App Store Connect / Ad Hoc
```

## 6. Zdroje dat

| Obchod | Zdroj | Metoda |
|--------|-------|--------|
| Penny | penny.cz | JSON API |
| Billa | billa.cz | JSON API |
| Lidl | lidl.cz | HTML scraping |
| Albert | kupi.cz | HTML + JSON-LD |
| Kaufland | kupi.cz | HTML + JSON-LD |
| Tesco | kupi.cz | HTML + JSON-LD |

## 7. Aktualizace dat

GitHub Actions automaticky spouští scraper každý den v 6:00 CET.
Workflow: `.github/workflows/update-slevy.yml`
