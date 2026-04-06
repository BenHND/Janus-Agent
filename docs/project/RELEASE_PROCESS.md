# Release Process Documentation

This document describes the process for creating and publishing releases of Janus.

## Table of Contents

- [Version Management](#version-management)
- [Release Preparation](#release-preparation)
- [Creating a Release](#creating-a-release)
- [Post-Release Tasks](#post-release-tasks)
- [Hotfix Process](#hotfix-process)

## Version Management

Janus follows [Semantic Versioning](https://semver.org/) (SemVer):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (1.X.0): New features, backward-compatible
- **PATCH** (1.0.X): Bug fixes, backward-compatible

### Version Files

The version number must be updated in multiple files:

1. **`janus/__init__.py`**: The authoritative version source
   ```python
   __version__ = "1.0.0"
   ```

2. **`setup.py`**: For package distribution
   ```python
   VERSION = '1.0.0'
   ```

3. **`CHANGELOG.md`**: Document the release
   ```markdown
   ## [1.0.0] - YYYY-MM-DD
   ```

### Determining the Next Version

Choose the version increment based on changes:

| Change Type | Version Increment | Example |
|-------------|-------------------|---------|
| Breaking changes / API changes | MAJOR | 1.0.0 → 2.0.0 |
| New features (backward-compatible) | MINOR | 1.0.0 → 1.1.0 |
| Bug fixes (backward-compatible) | PATCH | 1.0.0 → 1.0.1 |

## Release Preparation

### 1. Update Version Numbers

Update the version in all required files:

```bash
# Example: Updating to version 1.1.0
# 1. Update janus/__init__.py
sed -i '' 's/__version__ = ".*"/__version__ = "1.1.0"/' janus/__init__.py

# 2. Update setup.py
sed -i '' "s/VERSION = '.*'/VERSION = '1.1.0'/" setup.py
```

Or manually edit:
- `janus/__init__.py`: Update `__version__`
- `setup.py`: Update `VERSION`

### 2. Update CHANGELOG.md

1. **Move changes from [Unreleased] to a new version section**

   ```markdown
   ## [Unreleased]

   ## [1.1.0] - 2024-11-14

   ### Added
   - New feature X
   - New feature Y

   ### Fixed
   - Bug fix A
   - Bug fix B
   ```

2. **Add the new version link at the bottom**

   ```markdown
   [Unreleased]: https://github.com/BenHND/Janus/compare/v1.1.0...HEAD
   [1.1.0]: https://github.com/BenHND/Janus/releases/tag/v1.1.0
   [1.0.0]: https://github.com/BenHND/Janus/releases/tag/v1.0.0
   ```

### 3. Verify Changes

```bash
# Check version consistency
grep -n "__version__" janus/__init__.py
grep -n "VERSION" setup.py

# Test CLI version display
python main.py --version

# Run tests
python -m unittest discover tests

# Test build (optional)
./build_mac.sh
```

### 4. Commit Version Changes

```bash
git add janus/__init__.py setup.py CHANGELOG.md
git commit -m "Bump version to 1.1.0"
git push origin main
```

## Creating a Release

### 1. Create Git Tag

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Release version 1.1.0"

# Push tag to remote
git push origin v1.1.0
```

### 2. Build Application (macOS)

```bash
# Build the .app bundle
./build_mac.sh

# Sign and notarize (requires Apple Developer ID)
export DEVELOPER_ID_APPLICATION="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_ID="your.email@example.com"
export APPLE_ID_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export TEAM_ID="YOUR_TEAM_ID"
./scripts/sign_and_notarize.sh

# Create DMG installer
./scripts/create_dmg.sh
```

This produces:
- `dist/Janus.app` - Standalone application bundle
- `dist/Janus-1.1.0.dmg` - Installer for distribution

### 3. Test the Build

```bash
# Test on a clean macOS system without dev environment
# 1. Mount the DMG
# 2. Install the app
# 3. Run Janus and verify functionality
# 4. Check version: Open app, it should show v1.1.0
```

### 4. Create GitHub Release

#### Option A: Via GitHub Web Interface

1. Go to: `https://github.com/BenHND/Janus/releases/new`
2. **Choose tag**: Select `v1.1.0`
3. **Release title**: `Janus v1.1.0`
4. **Description**: Copy from CHANGELOG.md

   ```markdown
   ## What's New in v1.1.0

   ### Added
   - New feature X
   - New feature Y

   ### Fixed
   - Bug fix A
   - Bug fix B

   ## Installation

   Download `Janus-1.1.0.dmg`, open it, and drag Janus to Applications.

   ## Full Changelog

   See [CHANGELOG.md](https://github.com/BenHND/Janus/blob/main/CHANGELOG.md)
   ```

5. **Attach files**:
   - Upload `Janus-1.1.0.dmg`
   - Upload checksums (optional): `sha256sum Janus-1.1.0.dmg > checksums.txt`

6. **Publish release**

#### Option B: Via GitHub CLI

```bash
# Install GitHub CLI if needed
# brew install gh

# Create release with DMG
gh release create v1.1.0 \
  --title "Janus v1.1.0" \
  --notes-file release_notes.md \
  dist/Janus-1.1.0.dmg
```

### 5. Upload to Distribution Channels (Optional)

If you have additional distribution channels:

```bash
# Example: Upload to custom server
scp dist/Janus-1.1.0.dmg user@server:/releases/

# Example: Update homebrew cask (advanced)
# Update the cask formula with new version and sha256
```

## Post-Release Tasks

### 1. Update Documentation

Update any documentation that references version numbers:

```bash
# Update README.md if it has version-specific instructions
# Update installation guides
# Update quick start guides
```

### 2. Announce the Release

- Update project README.md with "Latest Release" badge
- Post on social media / blog (if applicable)
- Notify users via email list (if applicable)
- Update internal documentation

### 3. Create Next Development Version

Prepare for next development cycle:

```bash
# In CHANGELOG.md, add new [Unreleased] section
## [Unreleased]

### Added
### Changed
### Fixed

## [1.1.0] - 2024-11-14
...
```

Commit:
```bash
git add CHANGELOG.md
git commit -m "Prepare for next development cycle"
git push origin main
```

## Hotfix Process

For critical bugs that need immediate release:

### 1. Create Hotfix Branch

```bash
git checkout -b hotfix/1.1.1 v1.1.0
```

### 2. Fix the Bug

```bash
# Make necessary changes
git add .
git commit -m "Fix critical bug X"
```

### 3. Update Version (PATCH)

```bash
# Update version to 1.1.1
# Update CHANGELOG.md with hotfix details
```

### 4. Merge and Release

```bash
# Merge to main
git checkout main
git merge --no-ff hotfix/1.1.1

# Tag the hotfix
git tag -a v1.1.1 -m "Hotfix release 1.1.1"
git push origin main
git push origin v1.1.1

# Follow standard release process
```

### 5. Merge to Develop (if applicable)

```bash
git checkout develop
git merge --no-ff hotfix/1.1.1
git push origin develop
```

## Release Checklist

Use this checklist for each release:

### Pre-Release
- [ ] All tests pass: `python -m unittest discover tests`
- [ ] Version updated in `janus/__init__.py`
- [ ] Version updated in `setup.py`
- [ ] CHANGELOG.md updated with release notes
- [ ] CHANGELOG.md has correct date (YYYY-MM-DD)
- [ ] CHANGELOG.md has version comparison links
- [ ] Documentation updated
- [ ] Changes committed to `main` branch

### Release
- [ ] Git tag created: `git tag -a v1.x.x -m "Release 1.x.x"`
- [ ] Tag pushed: `git push origin v1.x.x`
- [ ] Application built: `./build_mac.sh`
- [ ] Application signed (if distributing)
- [ ] DMG created: `./scripts/create_dmg.sh`
- [ ] DMG tested on clean system

### GitHub Release
- [ ] GitHub release created
- [ ] Release notes added (from CHANGELOG)
- [ ] DMG attached to release
- [ ] Checksums provided (optional)
- [ ] Release published

### Post-Release
- [ ] Documentation updated
- [ ] README.md updated (if needed)
- [ ] Announcement made (if applicable)
- [ ] [Unreleased] section added to CHANGELOG.md
- [ ] Next development cycle prepared

## Automation (Future)

Consider automating the release process with GitHub Actions:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build macOS app
        run: ./build_mac.sh
      - name: Create DMG
        run: ./scripts/create_dmg.sh
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/Janus-*.dmg
```

**Note**: This is disabled by default to avoid unexpected costs. See README.md CI/CD section.

## Versioning Best Practices

1. **Never reuse version numbers**: Once released, a version is immutable
2. **Always test before releasing**: Run full test suite and manual tests
3. **Document breaking changes**: Clearly mark in CHANGELOG under a MAJOR version
4. **Keep CHANGELOG up-to-date**: Add entries as you develop, not just at release time
5. **Use semantic commits**: Help determine next version automatically
   - `feat:` → MINOR version bump
   - `fix:` → PATCH version bump
   - `BREAKING CHANGE:` → MAJOR version bump

## Questions?

For questions about the release process, contact the maintainer or open an issue on GitHub.
