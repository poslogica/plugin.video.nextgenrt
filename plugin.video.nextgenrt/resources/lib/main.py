import xbmcplugin
import xbmcgui
import xbmc
import sys
import re
try:
    from urllib.request import urlopen, Request
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urllib2 import urlopen, Request
    from urlparse import parse_qs
    from urllib import urlencode

# Plugin constants
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

# RT News streams with their titles - using original URLs
RT_STREAMS = [
    ("https://www.rt.com/on-air/", "Global"),
    ("https://www.rt.com/on-air/rt-america-air", "US"),
    ("https://rtd.rt.com/on-air/", "Documentaries"),
    ("https://actualidad.rt.com/en_vivo2", "ESP"),
    ("https://arabic.rt.com/live/", "ARAB"),
    ("https://de.rt.com/livetv/", "DE")
]

def _fetch_page_html(page_url):
    """Fetch HTML content from a page with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = Request(page_url, headers=headers)
    response = urlopen(req)
    return response.read().decode('utf-8')

def _extract_m3u8_url(html):
    """Extract m3u8 URL from HTML."""
    m = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT News - Found m3u8 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_file_pattern(html):
    """Extract URL from file: pattern."""
    m = re.search(r"file:\s*['\"]([^'\"]+)['\"]", html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT News - Found stream URL (file pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_url_pattern(html):
    """Extract URL from url: pattern with m3u8."""
    m = re.search(r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT News - Found stream URL (url pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_source_tag(html):
    """Extract URL from <source> tag."""
    m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT News - Found stream URL (source tag): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_from_iframe(html):
    """Extract stream URL from iframe embed."""
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
    if not m:
        return None
    
    iframe_url = m.group(1)
    
    # Skip Rumble iframes
    if 'rumble.com' in iframe_url:
        xbmc.log("NextGen RT News - Found Rumble iframe but cannot extract stream directly", xbmc.LOGWARNING)
        return None
    
    # Ensure full URL
    if not iframe_url.startswith('http'):
        iframe_url = 'https:' + iframe_url
    
    xbmc.log("NextGen RT News - Found iframe, fetching: %s" % iframe_url, xbmc.LOGINFO)
    
    try:
        iframe_html = _fetch_page_html(iframe_url)
        return _extract_m3u8_url(iframe_html)
    except Exception as e:
        xbmc.log("NextGen RT News - Error fetching iframe: %s" % str(e), xbmc.LOGWARNING)
        return None

def _extract_rtd_stream(html):
    """Extract stream URL from rtd.rt.com specific pattern."""
    m = re.search(r'streams_hls.+?url:\s*["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT News - Found stream URL (rtd pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _try_standard_patterns(html):
    """Try standard extraction patterns in order."""
    extractors = [
        _extract_m3u8_url,
        _extract_file_pattern,
        _extract_url_pattern,
        _extract_source_tag,
        _extract_from_iframe
    ]
    
    for extractor in extractors:
        url = extractor(html)
        if url:
            return url
    return None

def get_stream_url(page_url):
    """Extract the actual stream URL from the RT page."""
    try:
        xbmc.log("NextGen RT News - Fetching page: %s" % page_url, xbmc.LOGINFO)
        html = _fetch_page_html(page_url)
        
        # Check if this is rtd.rt.com (uses different pattern)
        if 'rtd.rt.com' in page_url:
            stream_url = _extract_rtd_stream(html)
        else:
            stream_url = _try_standard_patterns(html)
        
        if not stream_url:
            xbmc.log("NextGen RT News - No stream URL found in page", xbmc.LOGERROR)
        
        return stream_url
    except Exception as e:
        xbmc.log("NextGen RT News - Error getting stream URL: %s" % str(e), xbmc.LOGERROR)
        return None

def list_videos():
    """Create a list of RT News streams."""
    for url, name in RT_STREAMS:
        list_item = xbmcgui.ListItem(label="RT News - %s" % name)
        list_item.setInfo("video", {"title": "RT News - %s" % name, "genre": "News"})
        list_item.setProperty("IsPlayable", "true")
        
        # Create a URL with the page URL as a parameter
        plugin_url = "%s?action=play&url=%s" % (PLUGIN_URL, url)
        
        # Add the list item to the directory
        xbmcplugin.addDirectoryItem(
            handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=False
        )
    
    xbmcplugin.endOfDirectory(HANDLE)

def play_video(url):
    """Play a video from the given URL."""
    xbmc.log("NextGen RT News - Playing video from: %s" % url, xbmc.LOGINFO)
    stream_url = get_stream_url(url)
    
    if stream_url:
        xbmc.log("NextGen RT News - Resolved to stream: %s" % stream_url, xbmc.LOGINFO)
        
        # Create list item with the stream URL
        list_item = xbmcgui.ListItem(path=stream_url)
        
        # Set properties for HLS/m3u8 streams
        if '.m3u8' in stream_url:
            xbmc.log("NextGen RT News - Setting up HLS stream with inputstream.adaptive", xbmc.LOGINFO)
            # For Kodi 19+ (Matrix and later)
            list_item.setProperty('inputstream', 'inputstream.adaptive')
            list_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            list_item.setContentLookup(False)
            
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmc.log("NextGen RT News - Failed to resolve stream URL", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def run():
    """Main entry point for the plugin."""
    # Parse parameters
    params = {}
    if len(sys.argv) > 2:
        params_str = sys.argv[2]
        if params_str:
            if params_str.startswith('?'):
                params_str = params_str[1:]
            params = parse_qs(params_str)
            # Convert lists to single values
            params = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in params.items()}
    
    xbmc.log("NextGen RT News - Params: %s" % str(params), xbmc.LOGINFO)
    
    # Route to appropriate function
    action = params.get('action')
    if action == 'play':
        url = params.get('url')
        if url:
            play_video(url)
    else:
        list_videos()

if __name__ == "__main__":
    run()
