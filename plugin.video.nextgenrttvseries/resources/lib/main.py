import sys
import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import re
import gzip
import io
try:
    from urllib.request import urlopen, Request
    from urllib.parse import parse_qs
except ImportError:
    from urllib2 import urlopen, Request
    from urlparse import parse_qs

# Plugin constants
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

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

def _extract_m3u8_url(html):
    """Extract m3u8 URL from HTML."""
    m = re.search(r'(https?://[^"\s]+\.m3u8[^"\s]*)', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT TV Series - Found m3u8 URL: %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_file_pattern(html):
    """Extract URL from file: pattern."""
    m = re.search(r"file:\s*['\"]([^'\"]+)['\"]", html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT TV Series - Found stream URL (file pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_url_pattern(html):
    """Extract URL from url: pattern with m3u8."""
    m = re.search(r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT TV Series - Found stream URL (url pattern): %s" % m.group(1), xbmc.LOGINFO)
        return m.group(1)
    return None

def _extract_source_tag(html):
    """Extract URL from <source> tag."""
    m = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT TV Series - Found stream URL (source tag): %s" % m.group(1), xbmc.LOGINFO)
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
        xbmc.log("NextGen RT TV Series - Found Rumble iframe but cannot extract stream directly", xbmc.LOGWARNING)
        return None
    
    # Ensure full URL
    if not iframe_url.startswith('http'):
        iframe_url = 'https:' + iframe_url
    
    xbmc.log("NextGen RT TV Series - Found iframe, fetching: %s" % iframe_url, xbmc.LOGINFO)
    
    try:
        iframe_html = _fetch_page_html(iframe_url)
        return _extract_m3u8_url(iframe_html)
    except Exception as e:
        xbmc.log("NextGen RT TV Series - Error fetching iframe: %s" % str(e), xbmc.LOGWARNING)
        return None

def _extract_rtd_stream(html):
    """Extract stream URL from rtd.rt.com specific pattern."""
    m = re.search(r'streams_hls.+?url:\s*["\']([^"\']+)["\']', html, re.DOTALL)
    if m:
        xbmc.log("NextGen RT TV Series - Found stream URL (rtd pattern): %s" % m.group(1), xbmc.LOGINFO)
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
        xbmc.log("NextGen RT TV Series - Fetching page: %s" % page_url, xbmc.LOGINFO)
        html = _fetch_page_html(page_url)
        
        # RTD uses a specific pattern
        stream_url = _extract_rtd_stream(html)
        if not stream_url:
            stream_url = _try_standard_patterns(html)
        
        if not stream_url:
            xbmc.log("NextGen RT TV Series - No stream URL found in page", xbmc.LOGERROR)
        
        return stream_url
    except Exception as e:
        xbmc.log("NextGen RT TV Series - Error getting stream URL: %s" % str(e), xbmc.LOGERROR)
        return None

def _extract_series_list(html):
    """Extract series list from RTDoc serials page.
    
    Look for various HTML patterns for series links.
    """
    series = []
    
    # Try multiple patterns to find series links
    patterns = [
        # Pattern 1: Standard <a> tags with /serials/ in href
        r'<a\s+href="(https://en\.rtdoc\.tv/serials/[^"]+)"\s*>([^<]+)</a>',
        # Pattern 2: This pattern was working (36 matches found) - captures partial or full URLs
        r'href=["\']([^"\']*serials[^"\']+)["\'][^>]*>([^<]+)<',
        # Pattern 3: Broader search for any link with serials
        r'(https://en\.rtdoc\.tv/serials/[^\s"\'<>]+)[^>]*>([^<]+)</a>',
    ]
    
    seen = set()
    match_count = 0
    
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        match_count += len(matches)
        xbmc.log("NextGen RT TV Series - Pattern '%s' found %d matches" % (pattern[:50], len(matches)), xbmc.LOGINFO)
        
        for item in matches:
            if len(item) >= 2:
                url, title = item[0], item[1]
            else:
                continue
            
            # Ensure URL is complete - Pattern 2 may return partial URLs like /serials/123-title
            if not url.startswith('http'):
                url = 'https://en.rtdoc.tv' + url if url.startswith('/') else 'https://en.rtdoc.tv/' + url
                
            title_clean = title.strip()
            
            # Filter out navigation and very short titles
            if title_clean and url not in seen and len(title_clean) > 3:
                if title_clean.lower() not in ['films', 'tv series', 'on air', 'live', 'collections', 'profile']:
                    seen.add(url)
                    series.append({
                        'title': title_clean,
                        'url': url
                    })
                    xbmc.log("NextGen RT TV Series - Found series: %s -> %s" % (title_clean, url), xbmc.LOGDEBUG)
    
    xbmc.log("NextGen RT TV Series - Total patterns matched: %d, unique series: %d" % (match_count, len(series)), xbmc.LOGINFO)
    
    return series

def list_series():
    """Create a list of RT Documentary series from en.rtdoc.tv/serials."""
    try:
        xbmc.log("NextGen RT TV Series - Fetching series list from https://en.rtdoc.tv/serials", xbmc.LOGINFO)
        html = _fetch_page_html("https://en.rtdoc.tv/serials")
        series_list = _extract_series_list(html)
        
        if not series_list:
            xbmc.log("NextGen RT TV Series - No series found", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        for series in series_list:
            list_item = xbmcgui.ListItem(label=series['title'])
            list_item.setInfo("video", {"title": series['title']})
            
            # Create a URL to list episodes for this series
            plugin_url = "%s?action=episodes&url=%s" % (PLUGIN_URL, series['url'])
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=True
            )
        
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        xbmc.log("NextGen RT TV Series - Error listing series: %s" % str(e), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(HANDLE)

def _extract_episodes_list(html):
    """Extract episodes list from a series page with season info.
    
    Episodes are found with /episodes/ in the URL.
    Returns episodes with extracted season and episode numbers.
    """
    episodes = []
    
    # First, try to extract season headers (e.g., "2 Season", "1 Season")
    # Looking for patterns like "### [Episode X Title](url)" or similar markdown
    season_pattern = r'(\d+)\s+Season'
    season_matches = re.findall(season_pattern, html, re.IGNORECASE)
    
    xbmc.log("NextGen RT TV Series - Found season text: %s" % str(season_matches), xbmc.LOGINFO)
    
    # If we find seasons, use them; otherwise assume single season
    seasons = sorted({int(s) for s in season_matches}, reverse=True) if season_matches else [1]
    current_season = seasons[0] if seasons else 1
    
    xbmc.log("NextGen RT TV Series - Detected seasons: %s, starting with season %d" % (str(seasons), current_season), xbmc.LOGINFO)
    
    # Pattern that works: finds text followed by /episodes/ links
    # This pattern captures the episode title and the episode URL
    pattern = r'>([^<]*?)<\/a>\s*(?:</li>)?.*?href=["\']([^"\']*\/episodes\/[^"\']*)'
    
    seen = set()
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    
    xbmc.log("NextGen RT TV Series - Found %d episode matches" % len(matches), xbmc.LOGINFO)
    
    # For multi-season series, split episodes into seasons based on position
    # Episodes appear in groups on the page separated by season info
    # Since we detected len(seasons) seasons, divide episodes evenly
    if len(seasons) > 1 and len(matches) > 0:
        episodes_per_season = len(matches) // len(seasons)
        xbmc.log("NextGen RT TV Series - Dividing %d episodes into %d seasons (~%d per season)" % (len(matches), len(seasons), episodes_per_season), xbmc.LOGINFO)
        
        # Assign episodes to seasons based on their position
        season_idx = 0
        for ep_idx, match in enumerate(matches):
            if len(match) == 2:
                title, url = match[0].strip(), match[1]
                
                # Complete relative URLs
                if url.startswith('/'):
                    url = 'https://en.rtdoc.tv' + url
                
                if title and url not in seen and 'episodes' in url:
                    seen.add(url)
                    
                    # Determine which season based on position
                    # Episodes appear in order on page, grouped by season
                    # Start with highest season number, work down
                    current_season = seasons[season_idx // episodes_per_season] if season_idx < len(seasons) else seasons[-1]
                    
                    # Try to extract episode number
                    ep_match = re.search(r'Episode\s+(\d+)', title, re.IGNORECASE)
                    ep_num = int(ep_match.group(1)) if ep_match else None
                    
                    episodes.append({
                        'title': title,
                        'url': url,
                        'episode': ep_num,
                        'season': current_season
                    })
                    
                    season_idx += 1
    else:
        # Single season - simple processing
        for match in matches:
            if len(match) == 2:
                title, url = match[0].strip(), match[1]
                
                # Complete relative URLs
                if url.startswith('/'):
                    url = 'https://en.rtdoc.tv' + url
                
                if title and url not in seen and 'episodes' in url:
                    seen.add(url)
                    
                    # Try to extract episode number
                    ep_match = re.search(r'Episode\s+(\d+)', title, re.IGNORECASE)
                    ep_num = int(ep_match.group(1)) if ep_match else None
                    
                    episodes.append({
                        'title': title,
                        'url': url,
                        'episode': ep_num,
                        'season': 1
                    })
    
    # Log what we extracted
    unique_seasons = sorted(set(ep.get('season', 1) for ep in episodes))
    xbmc.log("NextGen RT TV Series - _extract_episodes_list: extracted %d episodes with seasons %s" % (len(episodes), str(unique_seasons)), xbmc.LOGINFO)
    
    return episodes

def list_episodes(series_url):
    """List episodes for a specific series, organized by season."""
    try:
        xbmc.log("NextGen RT TV Series - Fetching episodes from %s" % series_url, xbmc.LOGINFO)
        html = _fetch_page_html(series_url)
        episodes_list = _extract_episodes_list(html)
        
        if not episodes_list:
            xbmc.log("NextGen RT TV Series - No episodes found for series", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        # Group episodes by season
        episodes_by_season = {}
        for episode in episodes_list:
            season = episode.get('season', 1)
            if season not in episodes_by_season:
                episodes_by_season[season] = []
            episodes_by_season[season].append(episode)
        
        # Display seasons as folders if multiple seasons, otherwise show episodes directly
        seasons = sorted(episodes_by_season.keys(), reverse=True)
        
        if len(seasons) > 1:
            # Multiple seasons - create season folders
            for season in seasons:
                season_episodes = episodes_by_season[season]
                season_title = "Season %d (%d episodes)" % (season, len(season_episodes))
                list_item = xbmcgui.ListItem(label=season_title)
                list_item.setInfo("video", {"title": season_title})
                
                # Create a URL to list episodes for this season
                # We'll pass the season number as a parameter
                plugin_url = "%s?action=season_episodes&url=%s&season=%d" % (PLUGIN_URL, series_url, season)
                
                xbmcplugin.addDirectoryItem(
                    handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=True
                )
        else:
            # Single season - show episodes directly
            for episode in episodes_list:
                ep_num = episode.get('episode')
                ep_title = episode['title']
                
                # Format title with episode number if available
                if ep_num:
                    display_title = "S%dE%d - %s" % (episode.get('season', 1), ep_num, ep_title)
                else:
                    display_title = ep_title
                
                list_item = xbmcgui.ListItem(label=display_title)
                list_item.setProperty("IsPlayable", "true")
                
                info_tag = list_item.getVideoInfoTag()
                info_tag.setTitle(ep_title)
                if ep_num:
                    info_tag.setEpisode(ep_num)
                    info_tag.setSeason(episode.get('season', 1))
                try:
                    info_tag.setGenres(["Documentary"])
                except AttributeError:
                    pass
                
                # Create a URL to play this episode
                plugin_url = "%s?action=play&url=%s" % (PLUGIN_URL, episode['url'])
                
                xbmcplugin.addDirectoryItem(
                    handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=False
                )
        
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        xbmc.log("NextGen RT TV Series - Error listing episodes: %s" % str(e), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(HANDLE)

def play_series(url):
    """Play a series/episode from the given URL."""
    xbmc.log("NextGen RT TV Series - Playing from: %s" % url, xbmc.LOGINFO)
    stream_url = get_stream_url(url)
    
    if stream_url:
        xbmc.log("NextGen RT TV Series - Resolved to stream: %s" % stream_url, xbmc.LOGINFO)
        
        # Create list item with the stream URL
        list_item = xbmcgui.ListItem(path=stream_url)
        
        # Set properties for HLS/m3u8 streams
        if '.m3u8' in stream_url:
            xbmc.log("NextGen RT TV Series - Setting up HLS stream with inputstream.adaptive", xbmc.LOGINFO)
            # For Kodi 19+ (Matrix and later)
            list_item.setProperty('inputstream', 'inputstream.adaptive')
            list_item.setContentLookup(False)
            
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmc.log("NextGen RT TV Series - Failed to resolve stream URL", xbmc.LOGERROR)
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
    
    xbmc.log("NextGen RT TV Series - Params: %s" % str(params), xbmc.LOGINFO)
    
    # Route to appropriate function
    action = params.get('action')
    if action == 'play':
        url = params.get('url')
        if url:
            play_series(url)
    elif action == 'season_episodes':
        url = params.get('url')
        season = params.get('season')
        if url:
            list_episodes_for_season(url, int(season) if season else 1)
    elif action == 'episodes':
        url = params.get('url')
        if url:
            list_episodes(url)
    else:
        list_series()

def list_episodes_for_season(series_url, season_num):
    """List episodes for a specific season of a series."""
    try:
        xbmc.log("NextGen RT TV Series - Fetching episodes for season %d from %s" % (season_num, series_url), xbmc.LOGINFO)
        html = _fetch_page_html(series_url)
        episodes_list = _extract_episodes_list(html)
        
        # Filter episodes for this season
        season_episodes = [ep for ep in episodes_list if ep.get('season') == season_num]
        
        if not season_episodes:
            xbmc.log("NextGen RT TV Series - No episodes found for season %d" % season_num, xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        for episode in season_episodes:
            ep_num = episode.get('episode')
            ep_title = episode['title']
            
            # Format title with episode number if available
            if ep_num:
                display_title = "S%dE%d - %s" % (season_num, ep_num, ep_title)
            else:
                display_title = ep_title
            
            list_item = xbmcgui.ListItem(label=display_title)
            list_item.setProperty("IsPlayable", "true")
            
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(ep_title)
            if ep_num:
                info_tag.setEpisode(ep_num)
                info_tag.setSeason(season_num)
            try:
                info_tag.setGenres(["Documentary"])
            except AttributeError:
                pass
            
            # Create a URL to play this episode
            plugin_url = "%s?action=play&url=%s" % (PLUGIN_URL, episode['url'])
            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE, url=plugin_url, listitem=list_item, isFolder=False
            )
        
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        xbmc.log("NextGen RT TV Series - Error listing season episodes: %s" % str(e), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(HANDLE)

if __name__ == "__main__":
    run()
