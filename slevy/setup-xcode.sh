#!/bin/bash
# Spusť tento script po přihlášení k Macu pro dokončení iOS buildu
# Použití: bash ~/Desktop/navrhy-webu/slevy/setup-xcode.sh
set -e

echo "=== Přijímám Xcode licenci ==="
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -license accept

echo "=== Syncing iOS ==="
cd ~/Desktop/navrhy-webu/slevy
npx cap sync ios

echo "=== Building iOS archive ==="
xcodebuild \
  -workspace ios/App/App.xcworkspace \
  -scheme App \
  -configuration Release \
  -archivePath builds/SlevyDnes.xcarchive \
  archive \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGNING_ALLOWED=NO

echo ""
echo "=== HOTOVO ==="
echo "Archive: builds/SlevyDnes.xcarchive"
echo ""
echo "Pro podepsaný build otevři Xcode:"
echo "  npx cap open ios"
echo "  Product > Archive > Distribute"
