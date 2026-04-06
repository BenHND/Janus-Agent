# 🎁 Binary Distribution Guide

**TICKET-OPS-001: Standalone Binary Distribution with Nuitka**

This guide explains how to build and distribute standalone Janus binaries that don't require Python to be installed.

---

## Overview

Janus can be compiled into a standalone executable using Nuitka. This allows users to run Janus without:

- Installing Python
- Managing virtual environments
- Installing dependencies
- Dealing with version conflicts

The binary includes:
- Python interpreter
- All Python dependencies
- Janus code and modules
- Required data files

---

## Building Binaries

### Prerequisites

1. **Python 3.10+** installed
2. **UV package manager** (or pip)
3. **System dependencies** installed:
   - macOS: `brew install portaudio ffmpeg tesseract`
   - Linux: `sudo apt-get install portaudio19-dev ffmpeg tesseract-ocr patchelf`
   - Windows: Install dependencies via installers or Chocolatey

4. **Nuitka** and dependencies:
   ```bash
   pip install nuitka ordered-set
   ```

### Quick Build

Use the provided build script:

```bash
# Build for current platform
./build-nuitka.sh
```

This will:
1. Check system requirements
2. Install Nuitka if needed
3. Install project dependencies
4. Compile with Nuitka
5. Create standalone binary in `dist/`

### Manual Build

For more control over the build process:

#### macOS

```bash
python -m nuitka \
  --onefile \
  --assume-yes-for-downloads \
  --output-dir=dist \
  --macos-create-app-bundle \
  --macos-app-name=Janus \
  --macos-app-version=1.0.0 \
  --include-data-file=config.ini=config.ini \
  --include-data-file=.env.example=.env.example \
  --python-flag=no_site \
  --enable-plugin=anti-bloat \
  main.py
```

Creates: `dist/Janus.app`

#### Windows

```bash
python -m nuitka ^
  --onefile ^
  --assume-yes-for-downloads ^
  --output-dir=dist ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=resources/icon.ico ^
  --include-data-file=config.ini=config.ini ^
  --include-data-file=.env.example=.env.example ^
  --python-flag=no_site ^
  --enable-plugin=anti-bloat ^
  --output-filename=janus-windows-x86_64.exe ^
  main.py
```

Creates: `dist/janus-windows-x86_64.exe`

#### Linux

```bash
python -m nuitka \
  --onefile \
  --assume-yes-for-downloads \
  --output-dir=dist \
  --include-data-file=config.ini=config.ini \
  --include-data-file=.env.example=.env.example \
  --python-flag=no_site \
  --enable-plugin=anti-bloat \
  --output-filename=janus-linux-x86_64 \
  main.py
```

Creates: `dist/janus-linux-x86_64`

---

## Nuitka Options Explained

| Option | Purpose |
|--------|---------|
| `--onefile` | Create single executable with all dependencies (recommended) |
| `--standalone` | Create directory with all dependencies (alternative to onefile) |
| `--assume-yes-for-downloads` | Auto-download required tools |
| `--output-dir=dist` | Output directory |
| `--macos-create-app-bundle` | Create .app bundle (macOS) |
| `--windows-console-mode=disable` | Hide console (Windows GUI) |
| `--include-data-file` | Bundle data files |
| `--python-flag=no_site` | Don't load site.py (smaller) |
| `--enable-plugin=anti-bloat` | Remove unused code |

**Note:** `--onefile` and `--standalone` are mutually exclusive. Use `--onefile` for a single executable file (recommended for distribution), or `--standalone` for a directory with multiple files (faster startup).

### Advanced Options

For optimized builds:

```bash
# Optimize for speed
--lto=yes

# Optimize for size
--remove-output

# Include specific packages
--include-package=janus

# Exclude unwanted packages
--nofollow-import-to=matplotlib,scipy

# Multi-threaded compilation (faster)
--jobs=4
```

---

## Platform-Specific Instructions

### macOS

#### 1. Build the App

```bash
./build-nuitka.sh
```

#### 2. Create DMG Installer

```bash
# Simple DMG
hdiutil create -volname Janus \
  -srcfolder dist/Janus.app \
  -ov -format UDZO \
  dist/Janus-installer.dmg

# Or use create-dmg for fancier installer
brew install create-dmg
create-dmg \
  --volname "Janus Installer" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Janus.app" 200 190 \
  --hide-extension "Janus.app" \
  --app-drop-link 600 185 \
  "dist/Janus-installer.dmg" \
  "dist/"
```

#### 3. Code Signing (Optional but Recommended)

```bash
# Sign the app
codesign --force --deep --sign "Developer ID Application: Your Name" \
  dist/Janus.app

# Verify signature
codesign --verify --verbose dist/Janus.app

# Notarize with Apple
xcrun notarytool submit dist/Janus-installer.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"
```

### Windows

#### 1. Build the Executable

```bash
./build-nuitka.sh
```

#### 2. Create Installer with InnoSetup

Create `installer.iss`:

```inno
[Setup]
AppName=Janus
AppVersion=1.0.0
DefaultDirName={pf}\Janus
DefaultGroupName=Janus
OutputDir=dist
OutputBaseFilename=Janus-Setup-1.0.0
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\janus-windows-x86_64.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Janus"; Filename: "{app}\janus-windows-x86_64.exe"
Name: "{commondesktop}\Janus"; Filename: "{app}\janus-windows-x86_64.exe"
```

Compile:
```bash
iscc installer.iss
```

#### 3. Code Signing (Optional)

```bash
signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com dist/janus-windows-x86_64.exe
```

### Linux

#### 1. Build the Binary

```bash
./build-nuitka.sh
```

#### 2. Create AppImage (Recommended)

```bash
# Install appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppDir structure
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# Copy files
cp dist/janus-linux-x86_64 AppDir/usr/bin/janus
cp resources/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/janus.png

# Create desktop entry
cat > AppDir/usr/share/applications/janus.desktop << EOF
[Desktop Entry]
Name=Janus
Exec=janus
Icon=janus
Type=Application
Categories=Utility;
EOF

# Build AppImage
./appimagetool-x86_64.AppImage AppDir dist/Janus-x86_64.AppImage
```

#### 3. Create .deb Package

```bash
# Install dpkg-deb
sudo apt-get install dpkg-dev

# Create package structure
mkdir -p janus-1.0.0/DEBIAN
mkdir -p janus-1.0.0/usr/bin
mkdir -p janus-1.0.0/usr/share/applications
mkdir -p janus-1.0.0/usr/share/icons

# Copy files
cp dist/janus-linux-x86_64 janus-1.0.0/usr/bin/janus
chmod +x janus-1.0.0/usr/bin/janus

# Create control file
cat > janus-1.0.0/DEBIAN/control << EOF
Package: janus
Version: 1.0.0
Architecture: amd64
Maintainer: BenHND <ben@example.com>
Description: Voice-controlled computer automation
 Janus is a voice assistant for desktop automation
Depends: portaudio19-dev, ffmpeg, tesseract-ocr
EOF

# Build package
dpkg-deb --build janus-1.0.0
mv janus-1.0.0.deb dist/
```

---

## CI/CD Integration

### GitHub Actions

The project includes a workflow for automated builds:

1. **Activate the workflow:**
   ```bash
   cd .github/workflows
   mv build-binaries.yml.example build-binaries.yml
   git add build-binaries.yml
   git commit -m "Enable binary builds"
   git push
   ```

2. **Trigger builds:**
   - **On tag:** `git tag -a v1.0.0 -m "Release 1.0.0" && git push --tags`
   - **Manual:** Go to Actions tab → Build Binaries → Run workflow

3. **Download artifacts:**
   - Builds appear in Actions tab
   - Download from release page (if tagged)

### Build Matrix

The workflow builds for:
- macOS (Intel + Apple Silicon)
- Windows (x86_64)
- Linux (x86_64, ARM64)

---

## Testing Binaries

### Basic Tests

```bash
# Test the binary runs
./dist/janus-linux-x86_64 --version

# Test help output
./dist/janus-linux-x86_64 --help

# Test configuration loading
./dist/janus-linux-x86_64 --get-session
```

### Full Integration Test

1. **Copy to clean machine** (no Python installed)
2. **Run the binary**
3. **Test voice recognition**
4. **Test automation commands**
5. **Check error handling**

### Automated Testing

Create a test script:

```bash
#!/bin/bash
# test-binary.sh

BINARY="./dist/janus-linux-x86_64"

echo "Testing binary..."

# Test 1: Binary exists and is executable
if [ ! -x "$BINARY" ]; then
    echo "❌ Binary not executable"
    exit 1
fi

# Test 2: Help works
if ! "$BINARY" --help > /dev/null 2>&1; then
    echo "❌ Help command failed"
    exit 1
fi

# Test 3: Version info
if ! "$BINARY" --version > /dev/null 2>&1; then
    echo "❌ Version command failed"
    exit 1
fi

echo "✅ All tests passed"
```

---

## Distribution Checklist

Before releasing binaries:

- [ ] Build for all target platforms
- [ ] Test on clean machines (no Python)
- [ ] Sign binaries (macOS/Windows)
- [ ] Create installers (DMG/MSI/AppImage)
- [ ] Verify file sizes are reasonable
- [ ] Test microphone access permissions
- [ ] Test automation features
- [ ] Include README and LICENSE
- [ ] Create release notes
- [ ] Upload to GitHub Releases
- [ ] Update download links in docs

---

## Troubleshooting Builds

### Build Fails

**Issue:** Nuitka compilation error

**Solution:**
```bash
# Check Python version
python --version  # Must be 3.10+

# Update Nuitka
pip install --upgrade nuitka

# Clean build directory
rm -rf build/ dist/

# Try again with verbose output
python -m nuitka --verbose main.py
```

### Binary Too Large

**Issue:** Binary is several GB

**Solution:**
```bash
# Use anti-bloat plugin
--enable-plugin=anti-bloat

# Exclude heavy packages
--nofollow-import-to=matplotlib,scipy,pandas

# Use LTO (Link Time Optimization)
--lto=yes

# Strip debug symbols (Linux)
strip dist/janus-linux-x86_64
```

### Missing Dependencies at Runtime

**Issue:** Binary crashes with import errors

**Solution:**
```bash
# Include package explicitly
--include-package=missing_package

# Include data directory
--include-data-dir=models=models

# Check what's included
python -m nuitka --report main.py
```

### Slow Startup

**Issue:** Binary takes long to start

**Solution:**
- Use `--onefile` mode (faster startup)
- Reduce included packages
- Lazy-load heavy dependencies in code

---

## Size Optimization

Expected sizes:
- macOS: 200-400 MB
- Windows: 150-300 MB
- Linux: 150-300 MB

Tips to reduce size:
1. Exclude unused packages
2. Don't bundle models (download separately)
3. Use compression
4. Strip debug symbols

---

## Next Steps

- [UV Package Management Guide](07-uv-package-management.md) - Modern package management
- [Developer Guide](../developer/01-getting-started.md) - Contribute to Janus
- [Release Process](../project/RELEASE_PROCESS.md) - Publishing releases

---

**Need Help?**

- Check [Troubleshooting Guide](08-troubleshooting.md)
- Read [Nuitka Documentation](https://nuitka.net/doc/user-manual.html)
- Open an issue on [GitHub](https://github.com/BenHND/Janus/issues)
