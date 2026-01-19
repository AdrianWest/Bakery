# KiCad Plugin Manager Release Checklist

This checklist covers all steps needed to publish Bakery to the KiCad Plugin and Content Manager (PCM).

## Pre-Release Preparation

- [O] **Complete all testing**
  - Test on Windows with KiCad 9.0
  - Test on Linux with KiCad 9.0 (if possible)
  - Test with various project types (simple and complex)
  - Verify all features work correctly
  - Fix any remaining bugs

- [0] **Update version number** (if needed)
  - Update `metadata.json` version field
  - Update `constants.py` PLUGIN_VERSION constant
  - Update CHANGELOG.md with release date
  - Update README.md status (change "In Development" to "Released")

- [O] **Verify documentation is complete**
  - README.md is accurate and comprehensive
  - CHANGELOG.md includes all changes
  - All Python files have proper Doxygen docstrings
  - LICENSE file is present and correct

- [0] **Verify icon meets requirements**
  - resources/Bakery_Icon.png is at least 64x64 pixels (256x256 recommended)
  - Icon is clear and recognizable at small sizes
  - Icon is in PNG format

## Package Creation

- [ ] **Create release directory structure**
  ```
  Bakery-1.0.0/
  ├── plugins/
  │   ├── __init__.py
  │   ├── bakery_plugin.py
  │   ├── base_localizer.py
  │   ├── constants.py
  │   ├── footprint_localizer.py
  │   ├── symbol_localizer.py
  │   ├── library_manager.py
  │   ├── sexpr_parser.py
  │   ├── ui_components.py
  │   ├── backup_manager.py
  │   ├── utils.py
  │   └── metadata.json
  ├── resources/
  │   ├── Bakery_Icon.png
  │   └── Bakery_Icon_256x256.png
  ├── LICENSE
  ├── metadata.json (copy at root)
  └── README.md (optional but recommended)
  ```

- [ ] **Create ZIP package**
  - Archive the entire Bakery-1.0.0 directory as Bakery-1.0.0.zip
  - Ensure ZIP contains the correct folder structure
  - Test extracting the ZIP to verify structure

- [ ] **Calculate file sizes and hash**
  - Get ZIP file size in bytes: `(Get-Item Bakery-1.0.0.zip).Length`
  - Calculate SHA256 hash: `certutil -hashfile Bakery-1.0.0.zip SHA256`
  - Estimate installed size: `(Get-ChildItem -Recurse Bakery-1.0.0 | Measure-Object -Property Length -Sum).Sum`

- [ ] **Update metadata.json with actual values**
  - Update `download_sha256` with calculated hash
  - Update `download_size` with ZIP file size in bytes
  - Update `install_size` with estimated installed size in bytes
  - Change `status` from "testing" to "stable"

## GitHub Release

- [ ] **Create Git tag**
  ```powershell
  git tag -a v1.0.0 -m "Release version 1.0.0"
  git push origin v1.0.0
  ```

- [ ] **Create GitHub Release**
  - Go to https://github.com/AdrianWest/Bakery/releases/new
  - Select tag: v1.0.0
  - Release title: "Bakery v1.0.0"
  - Description: Copy from CHANGELOG.md
  - Attach Bakery-1.0.0.zip as binary asset
  - Publish release

- [ ] **Verify download URL**
  - Copy the direct download URL of the ZIP from GitHub release
  - URL should be: `https://github.com/AdrianWest/Bakery/releases/download/v1.0.0/Bakery-1.0.0.zip`
  - Verify URL works by downloading the file

- [ ] **Update metadata.json one final time**
  - Ensure `download_url` points to the correct GitHub release asset URL
  - Commit and push final metadata.json

## Submit to KiCad PCM

### Option A: Official KiCad PCM Repository (Recommended)

- [ ] **Fork the KiCad PCM repository**
  - Go to https://gitlab.com/kicad/addons/metadata
  - Click "Fork" button
  - Wait for fork to complete

- [ ] **Add your metadata**
  - Clone your fork locally
  - Copy your `metadata.json` to `packages/com.github.adrianwest.bakery.json`
  - Commit the file

- [ ] **Create Merge Request**
  - Push to your fork
  - Go to https://gitlab.com/kicad/addons/metadata/-/merge_requests
  - Click "New merge request"
  - Select your fork and branch
  - Title: "Add Bakery plugin v1.0.0"
  - Description: Brief description of the plugin and what it does
  - Submit merge request

- [ ] **Wait for review and approval**
  - KiCad team will review your submission
  - Address any feedback or requested changes
  - Once approved and merged, your plugin will appear in the PCM within 24 hours

### Option B: Self-Hosted Repository (Alternative)

- [ ] **Create PCM repository JSON**
  - Create a `repository.json` file with your plugin metadata
  - Host it on GitHub Pages or another web server

- [ ] **Document repository URL for users**
  - Update README.md with instructions to add your repository URL
  - Users add: `https://yourdomain.com/repository.json` to their PCM

## Post-Release

- [ ] **Test installation via PCM**
  - Open KiCad
  - Go to Plugin and Content Manager
  - Search for "Bakery"
  - Install the plugin
  - Verify it works correctly

- [ ] **Announce the release**
  - Post on KiCad forums
  - Share on social media (if applicable)
  - Update project README with PCM installation instructions

- [ ] **Monitor for issues**
  - Watch GitHub issues for bug reports
  - Respond to user questions
  - Plan future updates based on feedback

## Notes

- First release may take longer for KiCad team to review
- Ensure all URLs in metadata.json are publicly accessible
- Keep metadata.json in your repository for future updates
- For subsequent releases, update the version array in metadata.json
- Consider backward compatibility when updating

## Quick Reference Commands

### Calculate SHA256 (PowerShell)
```powershell
certutil -hashfile Bakery-1.0.0.zip SHA256
```

### Get file size (PowerShell)
```powershell
(Get-Item Bakery-1.0.0.zip).Length
```

### Get folder size (PowerShell)
```powershell
(Get-ChildItem -Recurse Bakery-1.0.0 | Measure-Object -Property Length -Sum).Sum
```

### Create ZIP (PowerShell)
```powershell
Compress-Archive -Path Bakery-1.0.0 -DestinationPath Bakery-1.0.0.zip
```
