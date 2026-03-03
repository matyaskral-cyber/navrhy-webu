#!/bin/bash
# Build iOS SlevyDnes app
set -e

cd "$(dirname "$0")"

echo "=== Syncing web assets ==="
npm run build
npx cap sync ios

echo "=== Building iOS archive ==="
xcodebuild -workspace ios/App/App.xcworkspace \
  -scheme App \
  -configuration Release \
  -archivePath builds/SlevyDnes.xcarchive \
  archive \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGNING_ALLOWED=NO

echo "=== Done ==="
echo "Archive at: builds/SlevyDnes.xcarchive"
echo ""
echo "For signed build, open in Xcode:"
echo "  npx cap open ios"
echo "Then: Product > Archive > Distribute"
