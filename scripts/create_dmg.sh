#!/bin/bash
# Create DMG installer for Janus macOS application
# Ticket 11.1: Mac Standalone Packaging

set -e

echo "================================================"
echo "Janus DMG Creator"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_NAME="Janus"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-1.0.0.dmg"
VOLUME_NAME="Janus Installer"
TMP_DMG="tmp_${DMG_NAME}"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}Error: Application not found at $APP_PATH${NC}"
    echo "Please run ./build_mac.sh first"
    exit 1
fi

echo "Step 1: Creating temporary DMG..."
hdiutil create -size 500m -fs HFS+ -volname "$VOLUME_NAME" "$TMP_DMG"
echo -e "${GREEN}✓ Temporary DMG created${NC}"

echo ""
echo "Step 2: Mounting DMG..."
MOUNT_DIR=$(hdiutil attach "$TMP_DMG" | grep Volumes | awk '{print $3}')
echo -e "${GREEN}✓ DMG mounted at $MOUNT_DIR${NC}"

echo ""
echo "Step 3: Copying application..."
cp -R "$APP_PATH" "$MOUNT_DIR/"
echo -e "${GREEN}✓ Application copied${NC}"

echo ""
echo "Step 4: Creating Applications symlink..."
ln -s /Applications "$MOUNT_DIR/Applications"
echo -e "${GREEN}✓ Symlink created${NC}"

echo ""
echo "Step 5: Creating README..."
cat > "$MOUNT_DIR/README.txt" << 'EOF'
Janus - Voice-Controlled Computer Automation for macOS

INSTALLATION
------------
1. Drag Janus.app to the Applications folder
2. Open System Preferences → Security & Privacy → Privacy
3. Grant microphone access to Janus
4. Grant accessibility permissions to Janus
5. Launch Janus from Applications

REQUIREMENTS
------------
- macOS 10.14 (Mojave) or later
- Microphone for voice input
- 2GB+ RAM recommended
- 1GB+ free disk space

SUPPORT
-------
For issues and documentation:
https://github.com/BenHND/Janus

Copyright © 2024 BenHND
EOF
echo -e "${GREEN}✓ README created${NC}"

echo ""
echo "Step 6: Unmounting DMG..."
hdiutil detach "$MOUNT_DIR"
echo -e "${GREEN}✓ DMG unmounted${NC}"

echo ""
echo "Step 7: Converting to final DMG..."
if [ -f "$DMG_NAME" ]; then
    rm "$DMG_NAME"
fi
hdiutil convert "$TMP_DMG" -format UDZO -o "$DMG_NAME"
echo -e "${GREEN}✓ Final DMG created${NC}"

echo ""
echo "Step 8: Cleaning up..."
rm "$TMP_DMG"
echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo "================================================"
echo -e "${GREEN}DMG created successfully!${NC}"
echo "================================================"
echo ""
echo "DMG: $DMG_NAME"
echo "Size: $(du -sh "$DMG_NAME" | cut -f1)"
echo ""
echo "To test the installer:"
echo "  open $DMG_NAME"
echo ""
