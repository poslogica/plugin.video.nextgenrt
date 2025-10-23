# Icon and Fanart Required

This plugin requires visual assets to be fully compliant with Kodi standards:

## icon.png
- **Required**: Yes
- **Dimensions**: 256x256 pixels or 512x512 pixels (recommended)
- **Format**: PNG with transparency
- **Location**: `plugin.video.nextgenrt/icon.png`
- **Purpose**: Displayed in Kodi's addon browser and menus

## fanart.jpg
- **Required**: Recommended
- **Dimensions**: 1280x720 pixels or 1920x1080 pixels (HD quality)
- **Format**: JPG
- **Location**: `plugin.video.nextgenrt/fanart.jpg`
- **Purpose**: Background image displayed when addon is selected

## How to Add

1. Create or find appropriate images:
   - **icon.png**: RT News logo or a simple news-themed icon
   - **fanart.jpg**: RT News branding or news-related background image

2. Place the files in the plugin root directory:
   ```
   plugin.video.nextgenrt/
   ├── icon.png         <-- Add here
   ├── fanart.jpg       <-- Add here
   ├── addon.xml
   └── ...
   ```

3. Ensure proper permissions and file formats

## Design Guidelines

- Use clear, recognizable imagery
- Avoid text-heavy designs (especially for icon.png)
- Ensure good contrast and visibility at small sizes
- Follow Kodi's visual style guidelines
- Respect trademark and copyright laws

## Temporary Solution

If you don't have design resources, you can:
- Use a simple solid color PNG with "RT" text for icon
- Use a blurred news-themed stock photo for fanart
- Download from Kodi addon repository examples

## Note

Without these files, the addon will still function but may appear less professional in the Kodi interface. Some Kodi repositories may reject submissions without proper visual assets.
