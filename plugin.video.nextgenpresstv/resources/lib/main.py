import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import sys
import re
import traceback
try:
    from urllib.request import urlopen, Request
    from urllib.parse import parse_qs
except ImportError:
    from urllib2 import urlopen, Request
    from urlparse import parse_qs

# Plugin constants
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

# PressTV streams
PRESSTV_CATEGORIES = [
    ("https://www.presstv.ir/doc/section/601", 32010, "Iran"),
    ("https://www.presstv.ir/doc/section/602", 32011, "Imperialism"),
    ("https://www.presstv.ir/doc/section/603", 32012, "Resistance"),
    ("https://www.presstv.ir/doc/section/604", 32013, "Biography"),
    ("https://www.presstv.ir/doc/section/605", 32014, "Religion"),
    ("https://www.presstv.ir/doc/section/606", 32015, "West Asia"),
    ("https://www.presstv.ir/doc/section/607", 32016, "World"),
    ("https://www.presstv.ir/Live", 32017, "Live Stream"),
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
        xbmc.log("NextGen PressTV - Found m3u8 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_mp4_url(html):
    """Extract MP4 URL from HTML."""
    # Look for preview.presstv.ir mp4 links
    m = re.search(r'(https?://preview\.presstv\.ir/[^"\s]+\.mp4[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen PressTV - Found MP4 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    # Fallback - look for any mp4 URL
    m = re.search(r'(https?://[^"\s]+\.mp4[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen PressTV - Found MP4 URL (fallback): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_file_pattern(html):
    """Extract URL from file: pattern."""
    m = re.search(r"file:\s*['\"]([^'\"]+)['\"]", html, re.DOTALL)
    if m:
        xbmc.log("NextGen PressTV - Found stream URL (file pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_url_pattern(html):
    """Extract URL from url: pattern with m3u8."""
    m = re.search(r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen PressTV - Found stream URL (url pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_source_tag(html):
    """Extract URL from <source> tag."""
    m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen PressTV - Found stream URL (source tag): %s" % m.group(1), xbmc.LOGINFO)
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
        xbmc.log("NextGen PressTV - Found Rumble iframe but cannot extract stream directly", xbmc.LOGWARNING)
        return None
    
    # Ensure full URL
    if not iframe_url.startswith('http'):
        iframe_url = 'https:' + iframe_url
    
    xbmc.log("NextGen PressTV - Found iframe, fetching: %s" % iframe_url, xbmc.LOGINFO)
    
    try:
        iframe_html = _fetch_page_html(iframe_url)
        return _extract_m3u8_url(iframe_html)
    except Exception as e:
        xbmc.log("NextGen PressTV - Error fetching iframe: %s" % str(e), xbmc.LOGWARNING)
        return None

def _extract_documentaries(html):
    """Extract documentary links from category page."""
    docs = []
    
    # Pattern for unquoted href attribute: href=/doc/Detail/2026/02/18/764305/Golden-Corridor->
    # Match href= followed by /doc/Detail/ and capture until we hit > or space
    pattern = r'href=(/doc/Detail/[^\s>]+)'
    matches = re.findall(pattern, html)
    
    if matches:
        # Process each URL found
        for url in matches:
            # Normalize URL
            if url.startswith('/'):
                url = 'https://www.presstv.ir' + url
            elif not url.startswith('http'):
                url = 'https://www.presstv.ir/' + url
            
            # Extract title from URL slug (last part after final /)
            url_parts = url.rstrip('/').split('/')
            if url_parts:
                slug = url_parts[-1]
                # Convert slug to readable title: "Golden-Corridor-" -> "Golden Corridor"
                title = slug.replace('-', ' ').strip()
                
                if title and len(title) > 2:
                    if (url, title) not in docs:
                        docs.append((url, title))
    
    xbmc.log("NextGen PressTV - Found %d documentaries" % len(docs), xbmc.LOGINFO)
    return docs

def _get_stream_url(page_url):
    """Get stream URL from page by trying multiple extraction patterns."""
    try:
        html = _fetch_page_html(page_url)
        
        # Try different extraction methods - MP4 first since that's what PressTV uses
        stream_url = (_extract_mp4_url(html) or
                     _extract_m3u8_url(html) or 
                     _extract_file_pattern(html) or 
                     _extract_url_pattern(html) or 
                     _extract_source_tag(html) or 
                     _extract_from_iframe(html))
        
        if stream_url:
            return stream_url
        else:
            xbmc.log("NextGen PressTV - Could not extract stream URL from %s" % page_url, xbmc.LOGWARNING)
            return None
            
    except Exception as e:
        xbmc.log("NextGen PressTV - Error getting stream: %s" % str(e), xbmc.LOGWARNING)
        return None

def _play_stream(stream_url):
    """Play a stream using the plugin."""
    if not stream_url:
        dialog = xbmcgui.Dialog()
        dialog.notification("NextGen PressTV", "Failed to resolve stream URL", xbmcgui.NOTIFICATION_ERROR)
        return
    
    # Use xbmc.executebuiltin to play the stream directly
    # This is more compatible across Kodi versions
    xbmc.log("NextGen PressTV - Playing: %s" % stream_url, xbmc.LOGINFO)
    xbmc.executebuiltin('PlayMedia(%s)' % stream_url)

def _show_streams():
    """Show available documentary categories."""
    for url, name_id, display_name in PRESSTV_CATEGORIES:
        list_item = xbmcgui.ListItem(label=xbmcaddon.Addon().getLocalizedString(name_id) or display_name)
        list_item.setArt({
            'icon': xbmcaddon.Addon().getAddonInfo('path') + '/icon.png',
            'fanart': xbmcaddon.Addon().getAddonInfo('path') + '/fanart.jpg'
        })
        info_tag = list_item.getVideoInfoTag()
        info_tag.setTitle(display_name)
        
        plugin_url = PLUGIN_URL + '?action=browse&url=' + url
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def _browse_documentaries(category_url):
    """Browse and list documentaries from a category page."""
    try:
        html = _fetch_page_html(category_url)
        documentaries = _extract_documentaries(html)
        
        if not documentaries:
            xbmc.log("NextGen PressTV - No documentaries found on %s" % category_url, xbmc.LOGWARNING)
            dialog = xbmcgui.Dialog()
            dialog.notification("NextGen PressTV", "No documentaries found", xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        xbmc.log("NextGen PressTV - Found %d documentaries" % len(documentaries), xbmc.LOGINFO)
        
        for doc_url, doc_title in documentaries:
            list_item = xbmcgui.ListItem(label=doc_title)
            list_item.setArt({
                'icon': xbmcaddon.Addon().getAddonInfo('path') + '/icon.png',
                'fanart': xbmcaddon.Addon().getAddonInfo('path') + '/fanart.jpg'
            })
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(doc_title)
            
            plugin_url = PLUGIN_URL + '?action=play&url=' + doc_url
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=False)
        
        xbmcplugin.endOfDirectory(HANDLE)
    except Exception as e:
        xbmc.log("NextGen PressTV - Error browsing documentaries: %s" % str(e), xbmc.LOGERROR)
        xbmc.log("NextGen PressTV - Traceback: %s" % traceback.format_exc(), xbmc.LOGERROR)
        dialog = xbmcgui.Dialog()
        dialog.notification("NextGen PressTV", "Error loading documentaries", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)

def run():
    """Main plugin entry point."""
    
    # Parse query parameters
    if len(sys.argv) > 2:
        params = parse_qs(sys.argv[2][1:])
        action = params.get('action', [''])[0]
        url = params.get('url', [''])[0]
        
        if action == 'browse' and url:
            xbmc.log("NextGen PressTV - Browsing documentaries from: %s" % url, xbmc.LOGINFO)
            _browse_documentaries(url)
        elif action == 'play' and url:
            xbmc.log("NextGen PressTV - Playing stream from: %s" % url, xbmc.LOGINFO)
            stream_url = _get_stream_url(url)
            _play_stream(stream_url)
        else:
            _show_streams()
    else:
        _show_streams()
