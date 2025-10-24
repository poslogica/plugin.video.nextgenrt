# GitHub Actions Workflow Updates - Both Plugins to Internet Archive

## Summary

✅ **The updated GitHub Actions workflow NOW:**

### 1. **Creates Both Plugin Zips**
```yaml
- name: Create plugin zips
  run: |
    zip -r plugin.video.nextgenrt-${{ steps.get_tag.outputs.NEW_VERSION }}.zip plugin.video.nextgenrt
    zip -r plugin.video.nextgenrttvseries-1.0.0.zip plugin.video.nextgenrttvseries
```
- Zips the main NextGen RT News plugin
- Zips the new TV Series plugin
- Both include their `resources/` folders with `icon.png` and `fanart.jpg`

### 2. **Creates GitHub Release with Both Plugins**
```yaml
- name: Create Release with Tag
  files: |
    plugin.video.nextgenrt-${{ steps.get_tag.outputs.NEW_VERSION }}.zip
    plugin.video.nextgenrttvseries-1.0.0.zip
```
- Both plugin zips are uploaded to GitHub Releases
- Users can download them directly from GitHub

### 3. **Downloads Both Plugins After Release**
```yaml
- name: Download latest release zips
  run: |
    # Download main plugin
    wget "...plugin.video.nextgenrt-${VERSION}.zip" -O plugin-downloads/...
    # Download TV series plugin
    wget "...plugin.video.nextgenrttvseries-1.0.0.zip" -O plugin-downloads/...
```
- Waits for release assets to be available
- Downloads both plugins from GitHub Releases

### 4. **Uploads Both Plugins + Assets to Internet Archive**
```yaml
- name: Upload plugin zips and assets to Internet Archive
  run: |
    # Upload main plugin icon/fanart
    ia upload "$IDENTIFIER" plugin.video.nextgenrt/icon.png plugin.video.nextgenrt/fanart.jpg
    
    # Upload TV series plugin icon/fanart
    ia upload "$IDENTIFIER" plugin.video.nextgenrttvseries/icon.png plugin.video.nextgenrttvseries/fanart.jpg
    
    # Upload main plugin zip
    ia upload "$IDENTIFIER" plugin-downloads/plugin.video.nextgenrt-*.zip
    
    # Upload TV series plugin zip
    ia upload "$IDENTIFIER" plugin-downloads/plugin.video.nextgenrttvseries-1.0.0.zip
    
    # Upload repository zip
    ia upload "$IDENTIFIER" downloads/repository.nextgenrt-*.zip
```
- All assets uploaded to Internet Archive item: `nextgenrtkodirepository`
- Both plugin zips uploaded
- Repository zip uploaded

### 5. **Updates addons.xml with Both Plugins**
```yaml
- name: Update addons.xml
  run: |
    # Extract from plugin.video.nextgenrt/addon.xml
    sed -n '/<addon/,/<\/addon>/p' plugin.video.nextgenrt/addon.xml >> addons.xml
    
    # Extract from plugin.video.nextgenrttvseries/addon.xml
    sed -n '/<addon/,/<\/addon>/p' plugin.video.nextgenrttvseries/addon.xml >> addons.xml
    
    # Extract from repository.nextgenrt/addon.xml
    sed -n '/<addon/,/<\/addon>/p' repository.nextgenrt/addon.xml >> addons.xml
    
    # Generate checksum
    md5sum addons.xml > addons.xml.md5
```
- Generates `addons.xml` with all 3 addons (main plugin, TV series plugin, repository)
- Generates MD5 checksum
- Both files uploaded to IA

## Internet Archive Structure After Upload

```
nextgenrtkodirepository/
├── plugin.video.nextgenrt/
│   ├── icon.png
│   └── fanart.jpg
├── plugin.video.nextgenrt-1.0.30.zip
├── plugin.video.nextgenrttvseries/
│   ├── icon.png
│   └── fanart.jpg
├── plugin.video.nextgenrttvseries-1.0.0.zip
├── repository.nextgenrt/
│   ├── icon.png
│   └── fanart.jpg
├── repository.nextgenrt-1.0.0.zip
├── addons.xml
└── addons.xml.md5
```

## What Users Can Do

**Option 1: Install via Repository (Recommended)**
1. In Kodi: Settings → Add-ons → Install from repository
2. Add source: `https://archive.org/download/nextgenrtkodirepository/`
3. Search for "NextGen RT" repository
4. Install it
5. Browse available plugins to install

**Option 2: Manual Install from Zip**
1. Download plugin zip from Internet Archive or GitHub Releases
2. In Kodi: Settings → Add-ons → Install from zip file
3. Select the downloaded zip

## Files Updated

- ✅ `.github/workflows/auto-release.yml` - Updated to handle both plugins

## Next Steps

1. Commit these workflow changes to your repo
2. Push to main branch
3. When you next bump a version, the workflow will:
   - Create zips for both plugins
   - Upload both plugins to IA
   - Update addons.xml with both plugins
   - Upload everything to IA

---

**Status:** ✅ **WORKFLOW READY FOR BOTH PLUGINS**

The GitHub Actions workflow now fully supports distributing both `plugin.video.nextgenrt` and `plugin.video.nextgenrttvseries` via Internet Archive!
