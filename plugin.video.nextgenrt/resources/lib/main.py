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
    ("https://arabic.rt.com/live/", "ARAB")
]

def get_stream_url(page_url):
    """Extract the actual stream URL from the RT page."""
    try:
        xbmc.log("NextGen RT News - Fetching page: %s" % page_url, xbmc.LOGINFO)
        
        # Create request with headers to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = Request(page_url, headers=headers)
        response = urlopen(req)
        html = response.read().decode('utf-8')
        
        # Try different regex patterns to find the stream URL
        if 'rtd.rt.com' not in page_url:
            # Pattern 1: Look for any .m3u8 URL in the page
            m = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', html, re.DOTALL)
            if m:
                xbmc.log("NextGen RT News - Found m3u8 URL: %s" % m.group(1), xbmc.LOGINFO)
                return m.group(1)
            
            # Pattern 2: file: 'url'
            m = re.search(r"file:\s*['\"]([^'\"]+)['\"]", html, re.DOTALL)
            if m:
                xbmc.log("NextGen RT News - Found stream URL (file pattern): %s" % m.group(1), xbmc.LOGINFO)
                return m.group(1)
            
            # Pattern 3: url: "*.m3u8"
            m = re.search(r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.DOTALL)
            if m:
                xbmc.log("NextGen RT News - Found stream URL (url pattern): %s" % m.group(1), xbmc.LOGINFO)
                return m.group(1)
            
            # Pattern 4: <source src="url"
            m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
            if m:
                xbmc.log("NextGen RT News - Found stream URL (source tag): %s" % m.group(1), xbmc.LOGINFO)
                return m.group(1)
            
            # Pattern 5: Check for Rumble or other video platform embeds
            # Extract video ID and try to get the actual stream
            m = re.search(r'rumble\.com/embed/([^/?"\s]+)', html, re.DOTALL)
            if m:
                rumble_id = m.group(1)
                xbmc.log("NextGen RT News - Found Rumble embed, trying to get stream for ID: %s" % rumble_id, xbmc.LOGINFO)
                # For now, return None and let other patterns try
                # In future, we could integrate with Rumble plugin
            
            # Pattern 6: Check for iframe with embedded player
            m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
            if m:
                iframe_url = m.group(1)
                if 'rumble.com' in iframe_url:
                    xbmc.log("NextGen RT News - Found Rumble iframe but cannot extract stream directly", xbmc.LOGWARNING)
                    # Skip Rumble iframes for now
                else:
                    if not iframe_url.startswith('http'):
                        iframe_url = 'https:' + iframe_url
                    xbmc.log("NextGen RT News - Found iframe, fetching: %s" % iframe_url, xbmc.LOGINFO)
                    # Fetch the iframe page with headers
                    iframe_req = Request(iframe_url, headers=headers)
                    iframe_response = urlopen(iframe_req)
                    iframe_html = iframe_response.read().decode('utf-8')
                    # Look for m3u8 in iframe
                    m2 = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', iframe_html, re.DOTALL)
                    if m2:
                        xbmc.log("NextGen RT News - Found m3u8 in iframe: %s" % m2.group(1), xbmc.LOGINFO)
                        return m2.group(1)
        else:
            # For rtd.rt.com, look for streams_hls
            m = re.search(r'streams_hls.+?url:\s*["\']([^"\']+)["\']', html, re.DOTALL)
            if m:
                xbmc.log("NextGen RT News - Found stream URL (rtd pattern): %s" % m.group(1), xbmc.LOGINFO)
                return m.group(1)
        
        # If no stream found, return None
        xbmc.log("NextGen RT News - No stream URL found in page", xbmc.LOGERROR)
        return None
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
