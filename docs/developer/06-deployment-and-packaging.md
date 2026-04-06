# Deployment & Packaging

Guide for building and deploying Janus on multiple platforms.

**🆕 NEW: Nuitka-based builds** - See [Binary Distribution Guide](08-binary-distribution.md) for standalone executables without Python.

## 📋 Table of Contents

1. [Modern Build Process (Nuitka)](#modern-build-process-nuitka)
2. [Legacy Build Process (py2app)](#legacy-build-process-py2app)
3. [Code Signing](#code-signing)
4. [Notarization](#notarization)

## Modern Build Process (Nuitka)

**Recommended for cross-platform distribution.**

### Quick Start

```bash
# Build for current platform
./build-nuitka.sh
```

Creates standalone executables:
- **macOS**: `dist/Janus.app` (app bundle)
- **Windows**: `dist/janus-windows-x86_64.exe`
- **Linux**: `dist/janus-linux-x86_64`

### Features

- ✅ No Python installation required
- ✅ Single executable file
- ✅ Includes all dependencies
- ✅ Cross-platform support
- ✅ Smaller file size than PyInstaller

### CI/CD Integration

See `.github/workflows/build-binaries.yml.example` for automated builds:

```bash
# Activate CI builds
cd .github/workflows
mv build-binaries.yml.example build-binaries.yml
git add . && git commit -m "Enable Nuitka builds" && git push
```

Builds trigger on:
- Git tags (e.g., `v1.0.0`)
- Manual workflow dispatch

### Full Documentation

For detailed Nuitka build instructions, see:
- [Binary Distribution Guide](08-binary-distribution.md)

## Legacy Build Process (py2app)

### Build Script

**File**: `build_mac.sh`

```bash
#!/bin/bash
# Build Janus for macOS distribution

set -e  # Exit on error

echo "🚀 Building Janus for macOS..."

# 1. Clean previous builds
rm -rf build/ dist/

# 2. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 3. Build with PyInstaller
pyinstaller \
    --name="Janus" \
    --windowed \
    --icon="resources/icon.icns" \
    --add-data="janus:janus" \
    --add-data="resources:resources" \
    --hidden-import="janus.core" \
    --hidden-import="janus.agents" \
    main.py

# 4. Copy models to app bundle
cp -r models/ dist/Janus.app/Contents/Resources/

echo "✅ Build complete: dist/Janus.app"
```

### Run Build

```bash
./build_mac.sh
```

## Code Signing

### Requirements

1. **Apple Developer Account** ($99/year)
2. **Developer ID Certificate** from Apple
3. **Xcode Command Line Tools**

### Sign Application

**File**: `scripts/sign_and_notarize.sh`

```bash
#!/bin/bash
# Sign and notarize Janus

APP_PATH="dist/Janus.app"
IDENTITY="Developer ID Application: Your Name (TEAM_ID)"

echo "🔏 Signing application..."

# Sign all frameworks and libraries
codesign --deep --force --verify --verbose \
    --sign "$IDENTITY" \
    --options runtime \
    "$APP_PATH"

echo "✅ Application signed"
```

### Verify Signature

```bash
codesign --verify --verbose=4 dist/Janus.app
spctl --assess --verbose=4 dist/Janus.app
```

## Notarization

### Submit for Notarization

```bash
# Create zip for notarization
ditto -c -k --keepParent dist/Janus.app Janus.zip

# Submit to Apple
xcrun notarytool submit Janus.zip \
    --apple-id "your@email.com" \
    --team-id "TEAM_ID" \
    --password "app-specific-password" \
    --wait

# Staple notarization ticket
xcrun stapler staple dist/Janus.app
```

### Verify Notarization

```bash
xcrun stapler validate dist/Janus.app
spctl -a -v dist/Janus.app
```

### Create DMG

```bash
# Create distributable DMG
./scripts/create_dmg.sh

# Output: dist/Janus-1.0.0.dmg
```

## Distribution Checklist

- [ ] Build application with `build_mac.sh`
- [ ] Sign application with Developer ID
- [ ] Notarize with Apple
- [ ] Staple notarization ticket
- [ ] Create DMG installer
- [ ] Test on clean macOS system
- [ ] Upload to GitHub Releases

---

**Documentation Complete!** 🎉

Return to [Developer Documentation Index](README.md)
