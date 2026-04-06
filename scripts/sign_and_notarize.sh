#!/bin/bash
# Code signing and notarization script for Janus macOS application
# Requires Apple Developer ID and valid certificates

set -e

echo "================================================"
echo "Janus Code Signing & Notarization"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_PATH="dist/Janus.app"
APP_NAME="Janus"
BUNDLE_ID="com.benhnd.janus"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}Error: Application not found at $APP_PATH${NC}"
    echo "Please run ./build_mac.sh first"
    exit 1
fi

# Check for required environment variables
if [ -z "$DEVELOPER_ID_APPLICATION" ]; then
    echo -e "${RED}Error: DEVELOPER_ID_APPLICATION environment variable not set${NC}"
    echo ""
    echo "Please set your Apple Developer ID certificate name:"
    echo "  export DEVELOPER_ID_APPLICATION=\"Developer ID Application: Your Name (TEAM_ID)\""
    echo ""
    echo "To find your certificate name, run:"
    echo "  security find-identity -v -p codesigning"
    exit 1
fi

if [ -z "$APPLE_ID" ]; then
    echo -e "${RED}Error: APPLE_ID environment variable not set${NC}"
    echo ""
    echo "Please set your Apple ID email:"
    echo "  export APPLE_ID=\"your.email@example.com\""
    exit 1
fi

if [ -z "$APPLE_ID_PASSWORD" ]; then
    echo -e "${YELLOW}Warning: APPLE_ID_PASSWORD not set${NC}"
    echo "You can create an app-specific password at: https://appleid.apple.com/account/manage"
    echo "  export APPLE_ID_PASSWORD=\"xxxx-xxxx-xxxx-xxxx\""
    echo ""
    read -p "Continue without password? (notarization will be skipped) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_NOTARIZATION=true
fi

if [ -z "$TEAM_ID" ]; then
    echo -e "${YELLOW}Warning: TEAM_ID not set (required for notarization)${NC}"
    echo "  export TEAM_ID=\"YOUR_TEAM_ID\""
    SKIP_NOTARIZATION=true
fi

echo "================================================"
echo "Configuration:"
echo "================================================"
echo "App Path: $APP_PATH"
echo "Bundle ID: $BUNDLE_ID"
echo "Developer ID: $DEVELOPER_ID_APPLICATION"
echo "Apple ID: $APPLE_ID"
echo "Team ID: ${TEAM_ID:-'Not set'}"
echo "Skip Notarization: ${SKIP_NOTARIZATION:-false}"
echo ""

# Step 1: Code Signing
echo "Step 1: Signing application bundle..."
echo "This will sign all frameworks, libraries, and executables..."

# Sign all nested frameworks and libraries first (inside-out)
find "$APP_PATH" \( -name "*.dylib" -o -name "*.so" -o -name "*.framework" \) -print0 | while IFS= read -r -d '' file; do
    echo "  Signing: $file"
    codesign --force --sign "$DEVELOPER_ID_APPLICATION" \
        --timestamp \
        --options runtime \
        --deep \
        "$file" 2>/dev/null || echo "    (already signed or skipped)"
done

# Sign the main application bundle
echo "  Signing main app bundle..."
codesign --force --sign "$DEVELOPER_ID_APPLICATION" \
    --timestamp \
    --options runtime \
    --deep \
    --entitlements <(cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
EOF
) "$APP_PATH"

echo -e "${GREEN}✓ Application signed successfully${NC}"

# Verify signature
echo ""
echo "Step 2: Verifying signature..."
codesign --verify --verbose=2 "$APP_PATH"
spctl --assess --verbose=4 --type execute "$APP_PATH" || echo "  (Gatekeeper check may fail before notarization)"
echo -e "${GREEN}✓ Signature verified${NC}"

# Step 3: Notarization (if credentials provided)
if [ "$SKIP_NOTARIZATION" = true ]; then
    echo ""
    echo -e "${YELLOW}Skipping notarization (credentials not provided)${NC}"
    echo ""
    echo "To enable notarization, set:"
    echo "  export APPLE_ID=\"your.email@example.com\""
    echo "  export APPLE_ID_PASSWORD=\"xxxx-xxxx-xxxx-xxxx\""
    echo "  export TEAM_ID=\"YOUR_TEAM_ID\""
    exit 0
fi

echo ""
echo "Step 3: Creating ZIP for notarization..."
ZIP_PATH="${APP_NAME}.zip"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"
echo -e "${GREEN}✓ ZIP created: $ZIP_PATH${NC}"

echo ""
echo "Step 4: Submitting for notarization..."
echo "This may take several minutes..."

# Submit for notarization
xcrun notarytool submit "$ZIP_PATH" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_ID_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

NOTARIZATION_STATUS=$?

if [ $NOTARIZATION_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Notarization successful${NC}"

    echo ""
    echo "Step 5: Stapling notarization ticket..."
    xcrun stapler staple "$APP_PATH"
    echo -e "${GREEN}✓ Notarization ticket stapled${NC}"

    echo ""
    echo "Step 6: Final verification..."
    spctl --assess --verbose=4 --type execute "$APP_PATH"
    echo -e "${GREEN}✓ Application is fully signed and notarized${NC}"
else
    echo -e "${RED}✗ Notarization failed${NC}"
    echo "Check the notarization log for details"
    exit 1
fi

# Cleanup
echo ""
echo "Cleaning up..."
rm -f "$ZIP_PATH"

echo ""
echo "================================================"
echo -e "${GREEN}Code signing and notarization complete!${NC}"
echo "================================================"
echo ""
echo "The application is now ready for distribution."
echo ""
echo "Next steps:"
echo "  1. Create DMG: ./scripts/create_dmg.sh"
echo "  2. Test on a different Mac to verify signature"
echo "  3. Distribute to users"
echo ""
