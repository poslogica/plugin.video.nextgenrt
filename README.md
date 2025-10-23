# NextGen RT News - Kodi Video Plugin

A Kodi video plugin that streams RT News live channels directly in Kodi.

## Description

NextGen RT News is a Kodi addon that provides access to RT (Russia Today) News live streams.
The plugin automatically extracts stream URLs from RT's web pages and plays them using Kodi's built-in video player with HLS (HTTP Live Streaming) support.

## Features

- **5 Live RT News Channels**:
  - **Global** - Main RT News English channel
  - **US** - RT America
  - **Documentaries** - RT Documentary channel
  - **ESP** - RT Spanish (Actualidad RT)
  - **ARAB** - RT Arabic

- **Automatic Stream Detection** - The plugin scrapes RT web pages to find and extract the actual m3u8 stream URLs
- **HLS Streaming Support** - Uses inputstream.adaptive for reliable HLS stream playback
- **Simple Interface** - Clean channel list with one-click playback

## Requirements

- Kodi 19 (Matrix) or later
- Python 3.x support in Kodi
- **InputStream Adaptive** addon (automatically installed as a dependency)

## Installation

### Method 1: Install from ZIP file

1. Download the latest release zip file from [GitHub Releases](https://github.com/poslogica/plugin.video.nextgenrt/releases/latest)
2. In Kodi, go to **Settings** → **Add-ons**
3. Enable **Unknown sources** if not already enabled
4. Select **Install from zip file**
5. Navigate to and select the downloaded zip file
6. Wait for the addon installation notification
7. The plugin will automatically install **InputStream Adaptive** if needed

### Method 2: Manual Installation

1. Copy the `plugin.video.nextgenrt` folder to your Kodi addons directory:
   - **Windows**: `%APPDATA%\Kodi\addons\`
   - **Linux**: `~/.kodi/addons/`
   - **macOS**: `~/Library/Application Support/Kodi/addons/`
2. Restart Kodi
3. Make sure **InputStream Adaptive** is installed from the Kodi repository

## Usage

1. Go to **Add-ons** → **Video add-ons**
2. Select **NextGen RT News**
3. Choose a channel from the list
4. The stream will start playing automatically

## Technical Details

- **Language**: Python 3
- **Video Format**: HLS (m3u8)
- **Stream Resolution**: Determined by RT's source (typically HD quality)
- **Dependencies**:
  - xbmc.python (3.0.1+)
  - inputstream.adaptive

## Troubleshooting

### Stream won't play

- Ensure **InputStream Adaptive** is installed and enabled
- Check your internet connection
- Some streams may be geo-blocked in certain regions

### Plugin doesn't appear

- Verify the plugin is installed in the correct addons directory
- Check Kodi logs for errors: `Settings → System → Logging → Enable debug logging`

### No channels listed

- Restart Kodi
- Check if the addon is enabled: `Settings → Add-ons → My add-ons → Video add-ons`

## Development

### Project Structure

```text
plugin.video.nextgenrt/
├── addon.xml                 # Plugin metadata and dependencies
├── default.py               # Entry point
├── resources/
│   ├── __init__.py
│   ├── settings.xml         # Plugin settings (future use)
│   ├── lib/
│   │   ├── __init__.py
│   │   └── main.py          # Main plugin logic and stream handling
│   └── language/
│       └── en-US/           # English language strings
```

### How It Works

1. **User selects a channel** from the plugin menu
2. **Plugin fetches the RT webpage** for that channel with proper User-Agent headers
3. **Regex patterns extract** the m3u8 stream URL from the page HTML
4. **Stream URL is passed** to Kodi with inputstream.adaptive configuration
5. **Video plays** using Kodi's video player

## License

GNU GENERAL PUBLIC LICENSE Version 2, June 1991

## Disclaimer

This plugin is not affiliated with or endorsed by RT (Russia Today).
It simply provides a convenient way to access publicly available RT News streams within Kodi.
Users are responsible for ensuring their use complies with RT's terms of service and local regulations.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Changelog

### v1.0.0 (2025-10-23)

- Initial release
- Support for 5 RT News live channels
- Automatic stream URL extraction
- HLS streaming with inputstream.adaptive
- Required dependency on inputstream.adaptive

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.
