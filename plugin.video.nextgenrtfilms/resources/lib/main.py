import sys
import xbmcplugin
import xbmcgui
import xbmc
import re
import gzip
try:
    from urllib.request import urlopen, Request
    from urllib.parse import parse_qs, quote_plus
    import json
except ImportError:
    from urllib2 import urlopen, Request
    from urlparse import parse_qs
    from urllib import quote_plus
    import json

# Plugin constants
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

# RT Films API URL
FILMS_API_URL = "https://rtd.rt.com/films/?json=true&letter=&order=aired&page={page}&search="
FILMS_BASE_URL = "https://rtd.rt.com"

def _fetch_page_html(page_url):
    """Fetch HTML content from a page with proper headers and gzip decompression."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = Request(page_url, headers=headers)
    response = urlopen(req)
    
    # Handle gzip-compressed responses
    if response.headers.get('Content-Encoding') == 'gzip':
        html = gzip.decompress(response.read()).decode('utf-8')
    else:
        html = response.read().decode('utf-8')
    
    return html

def _fetch_films_json(page=1):
    """Fetch films data from the JSON API."""
    api_url = FILMS_API_URL.format(page=page)
    xbmc.log("NextGen RT Films - Fetching API: %s" % api_url, xbmc.LOGINFO)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = Request(api_url, headers=headers)
    response = urlopen(req)
    
    # Handle gzip-compressed responses
    if response.headers.get('Content-Encoding') == 'gzip':
        data = gzip.decompress(response.read()).decode('utf-8')
    else:
        data = response.read().decode('utf-8')
    
    return json.loads(data)

def _extract_films_from_json(json_data):
    """Extract list of films from JSON API response."""
    films = []
    
    try:
        films_data = json_data.get('json_data', {}).get('films', [])
        
        for film_data in films_data:
            title = film_data.get('title', '').strip()
            film_url = film_data.get('film_url', '').strip()
            
            if not title or not film_url:
                continue
            
            # Build full URL
            if not film_url.startswith('http'):
                film_url = FILMS_BASE_URL + film_url
            
            # Get additional info
            headline = film_data.get('headline', '')
            title_extra = film_data.get('title_extra', '')
            thumbnail = film_data.get('filename', '')
            
            films.append({
                'title': title,
                'url': film_url,
                'category': headline,
                'plot': title_extra,
                'thumbnail': thumbnail
            })
        
        xbmc.log("NextGen RT Films - Extracted %d films from JSON" % len(films), xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log("NextGen RT Films - Error parsing JSON: %s" % str(e), xbmc.LOGERROR)
    
    return films

def _get_pagination_info(json_data):
    """Extract pagination information from JSON response."""
    try:
        pager = json_data.get('json_data', {}).get('pager_data', {})
        return {
            'current_page': pager.get('current_page', 1),
            'last_page': pager.get('last_page', 1),
            'first_page': pager.get('first_page', 1),
            'total_entries': pager.get('total_entries', 0)
        }
    except Exception as e:
        xbmc.log("NextGen RT Films - Error getting pagination: %s" % str(e), xbmc.LOGERROR)
        return {'current_page': 1, 'last_page': 1, 'first_page': 1, 'total_entries': 0}

def _extract_films_list(html):
    """Extract list of films from the films page (deprecated - kept for compatibility)."""
    films = []
    
    # Pattern 1: Match main-player__name (title) followed by button link
    # <div class="main-player__name">Title</div>...<a class="btn btn_4" href="/films/slug/">
    pattern1 = r'<div class="main-player__name">([^<]+)</div>.*?href="(/films/[^"]+)"'
    matches1 = re.findall(pattern1, html, re.DOTALL)
    
    for title, url in matches1:
        # Skip RSS and category pages
        if '/rss/' in url or url.endswith('/films/') or '-documentaries/' in url:
            continue
        
        # Clean up title
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)
        
        # Build full URL if needed
        if not url.startswith('http'):
            url = 'https://rtd.rt.com' + url
        
        films.append({
            'title': title,
            'url': url
        })
    
    # Pattern 2: Find button links with "watch film" text
    if not films:
        pattern2 = r'<a class="btn[^"]*"[^>]*href="(/films/[^"]+)"[^>]*>watch film</a>'
        urls = re.findall(pattern2, html, re.IGNORECASE)
        for url in urls:
            if '/rss/' not in url and not url.endswith('/films/') and '-documentaries/' not in url:
                # Extract title from URL slug
                slug = url.split('/')[-2]
                title = slug.replace('-', ' ').title()
                
                if not url.startswith('http'):
                    url = 'https://rtd.rt.com' + url
                
                films.append({
                    'title': title,
                    'url': url
                })
    
    # Remove duplicates
    seen = set()
    unique_films = []
    for film in films:
        if film['url'] not in seen:
            seen.add(film['url'])
            unique_films.append(film)
    
    return unique_films

def _extract_m3u8_url(html):
    """Extract m3u8 URL from HTML."""
    m = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found m3u8 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_file_pattern(html):
    """Extract URL from file: pattern."""
    m = re.search(r"file:\s*['\"]([^'\"]+)['\"]", html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found stream URL (file pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_url_pattern(html):
    """Extract URL from url: pattern with m3u8."""
    m = re.search(r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found stream URL (url pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_source_tag(html):
    """Extract URL from <source> tag."""
    m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found stream URL (source tag): %s" % m.group(1), xbmc.LOGINFO)
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
        xbmc.log("NextGen RT Films - Found Rumble iframe but cannot extract stream directly", xbmc.LOGWARNING)
        return None
    
    # Ensure full URL
    if not iframe_url.startswith('http'):
        iframe_url = 'https:' + iframe_url
    
    xbmc.log("NextGen RT Films - Found iframe, fetching: %s" % iframe_url, xbmc.LOGINFO)
    
    try:
        iframe_html = _fetch_page_html(iframe_url)
        return _extract_m3u8_url(iframe_html)
    except Exception as e:
        xbmc.log("NextGen RT Films - Error fetching iframe: %s" % str(e), xbmc.LOGWARNING)
        return None

def _extract_rtd_stream(html):
    """Extract stream URL from rtd.rt.com specific pattern."""
    m = re.search(r'streams_hls.+?url:\s*["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found stream URL (rtd pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_mp4_url(html):
    """Extract MP4 URL from HTML."""
    # Look for direct mp4 links
    m = re.search(r'(https?://[^"\s]+\.mp4[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT Films - Found MP4 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _try_standard_patterns(html):
    """Try standard extraction patterns in order."""
    extractors = [
        _extract_m3u8_url,
        _extract_file_pattern,
        _extract_url_pattern,
        _extract_source_tag,
        _extract_rtd_stream,
        _extract_mp4_url,
        _extract_from_iframe
    ]
    
    for extractor in extractors:
        url = extractor(html)
        if url:
            return url
    return None

def get_stream_url(page_url):
    """Extract the actual stream URL from the film page."""
    try:
        xbmc.log("NextGen RT Films - Fetching page: %s" % page_url, xbmc.LOGINFO)
        html = _fetch_page_html(page_url)
        
        stream_url = _try_standard_patterns(html)
        
        if not stream_url:
            xbmc.log("NextGen RT Films - No stream URL found in page", xbmc.LOGERROR)
        
        return stream_url
    except Exception as e:
        xbmc.log("NextGen RT Films - Error getting stream URL: %s" % str(e), xbmc.LOGERROR)
        return None

def list_films(page=1):
    """Create a list of RT Films from the JSON API with pagination."""
    try:
        xbmc.log("NextGen RT Films - Fetching films list (page %d)" % page, xbmc.LOGINFO)
        
        # Fetch data from JSON API
        json_data = _fetch_films_json(page)
        films = _extract_films_from_json(json_data)
        pagination = _get_pagination_info(json_data)
        
        if not films:
            xbmc.log("NextGen RT Films - No films found", xbmc.LOGWARNING)
            # Add a message item
            list_item = xbmcgui.ListItem(label="No films found. Please check the website.")
            xbmcplugin.addDirectoryItem(handle=HANDLE, url="", listitem=list_item, isFolder=False)
        else:
            xbmc.log("NextGen RT Films - Found %d films (page %d of %d, total: %d)" % 
                    (len(films), pagination['current_page'], pagination['last_page'], pagination['total_entries']), 
                    xbmc.LOGINFO)
            
            # Add film items
            for film in films:
                list_item = xbmcgui.ListItem(label=film['title'])
                
                # Set video info
                info_tag = list_item.getVideoInfoTag()
                info_tag.setTitle(film['title'])
                if film.get('plot'):
                    info_tag.setPlot(film['plot'])
                if film.get('category'):
                    try:
                        info_tag.setGenres([film['category']])
                    except AttributeError:
                        pass
                
                # Set thumbnail
                if film.get('thumbnail'):
                    list_item.setArt({'thumb': film['thumbnail'], 'poster': film['thumbnail']})
                
                list_item.setProperty("IsPlayable", "true")
                
                # Create a URL with the film URL as a parameter
                plugin_url = "%s?action=play&url=%s" % (PLUGIN_URL, quote_plus(film['url']))
                
                # Add the list item to the directory
                xbmcplugin.addDirectoryItem(
                    handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=False
                )
            
            # Add pagination controls
            current_page = pagination['current_page']
            last_page = pagination['last_page']
            
            # Add "Next Page" if not on last page
            if current_page < last_page:
                next_item = xbmcgui.ListItem(label="[COLOR yellow]Next Page (%d/%d) →[/COLOR]" % (current_page + 1, last_page))
                next_item.setProperty("IsPlayable", "false")
                next_url = "%s?action=list&page=%d" % (PLUGIN_URL, current_page + 1)
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_url, listitem=next_item, isFolder=True)
            
            # Add "Previous Page" if not on first page
            if current_page > 1:
                prev_item = xbmcgui.ListItem(label="[COLOR yellow]← Previous Page (%d/%d)[/COLOR]" % (current_page - 1, last_page))
                prev_item.setProperty("IsPlayable", "false")
                prev_url = "%s?action=list&page=%d" % (PLUGIN_URL, current_page - 1)
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=prev_url, listitem=prev_item, isFolder=True)
            
            # Add page info at the end
            info_text = "[COLOR gray]Page %d of %d - %d total films[/COLOR]" % (current_page, last_page, pagination['total_entries'])
            info_item = xbmcgui.ListItem(label=info_text)
            info_item.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(handle=HANDLE, url="", listitem=info_item, isFolder=False)
        
        xbmcplugin.endOfDirectory(HANDLE)
    except Exception as e:
        xbmc.log("NextGen RT Films - Error listing films: %s" % str(e), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def play_video(url):
    """Play a video from the given URL."""
    xbmc.log("NextGen RT Films - Playing video from: %s" % url, xbmc.LOGINFO)
    stream_url = get_stream_url(url)
    
    if stream_url:
        xbmc.log("NextGen RT Films - Resolved to stream: %s" % stream_url, xbmc.LOGINFO)
        
        # Create list item with the stream URL
        list_item = xbmcgui.ListItem(path=stream_url)
        
        # Set properties for HLS/m3u8 streams
        if '.m3u8' in stream_url:
            xbmc.log("NextGen RT Films - Setting up HLS stream with inputstream.adaptive", xbmc.LOGINFO)
            # For Kodi 19+ (Matrix and later)
            list_item.setProperty('inputstream', 'inputstream.adaptive')
            list_item.setContentLookup(False)
        
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmc.log("NextGen RT Films - Failed to resolve stream URL", xbmc.LOGERROR)
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
    
    xbmc.log("NextGen RT Films - Params: %s" % str(params), xbmc.LOGINFO)
    
    # Route to appropriate function
    action = params.get('action')
    
    if action == 'play':
        url = params.get('url')
        if url:
            play_video(url)
    elif action == 'list':
        # List films with page parameter
        page = int(params.get('page', 1))
        list_films(page)
    else:
        # Default: show first page
        list_films(1)

if __name__ == "__main__":
    run()
