import os
import re
import asyncio
import aiohttp
import yt_dlp
from typing import Optional

class YandexMusicHandler:
    def __init__(self):
        # We no longer need yandex-music-python or a token
        pass

    async def get_track_info(self, url: str) -> Optional[dict]:
        # Extract track ID
        match = re.search(r'track/(\d+)', url)
        if not match:
            return None
        
        track_id = match.group(1)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://music.yandex.ru/',
        }
        
        try:
            api_url = f"https://music.yandex.ru/handlers/track.jsx?track={track_id}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        print(f"Error: Yandex API status {resp.status}")
                        return None
                    data = await resp.json()
                    
                    # Track info is in 'track' key
                    track = data.get('track', {})
                    if not track:
                         # Sometimes it's in root if single track request?
                         track = data
                    
                    title = track.get('title', 'Unknown Title')
                    artists = [a.get('name') for a in track.get('artists', [])]
                    artist_str = ", ".join(artists) if artists else "Unknown Artist"
                    
                    # Clean up title (remove ' (Remix)' etc if needed, but better keep it)
                    
            print(f"Extracted: {artist_str} - {title}")
            
            query = f"{artist_str} - {title}"
            return {
                'query': query,
                'title': title,
                'artist': artist_str,
                'filename': f"{artist_str} - {title}.mp3".replace('/', '_').replace('\\', '_')
            }
        except Exception as e:
            print(f"Exception in get_track_info: {e}")
            return None

    async def download_track(self, query: str, filename: str) -> str:
        temp_path = os.path.join('/tmp' if os.name != 'nt' else '.', filename)
        
        # Advanced options to bypass YouTube bot detection
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_path.replace('.mp3', ''),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'impersonate': 'chrome', # Mimic Chrome browser at a low level
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music', 'web_creator', 'ios', 'android', 'tv'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
            'noprogress': True,
            'no_color': True,
        }

        # Check for cookies file
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"

        def run_ydl():
            # Attempt 1: YouTube
            try:
                print(f"Searching YouTube for: {query}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"ytsearch1:{query} audio"])
                return temp_path
            except Exception as e:
                print(f"YouTube download failed: {e}")
            
            # Attempt 2: SoundCloud
            try:
                print(f"Searching SoundCloud for: {query}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"scsearch1:{query}"])
                return temp_path
            except Exception as e:
                print(f"SoundCloud download failed: {e}")
                return ""

        # Run in thread pool
        path = await asyncio.to_thread(run_ydl)
        # Verify file exists (yt-dlp might fail silently or produce file with different name)
        # yt-dlp handling of outtmpl usually ensures correct name, but let's check
        if os.path.exists(temp_path):
             return temp_path
             
        # Check if file with .mp3 exists (in case conversion happened)
        if os.path.exists(temp_path):
            return temp_path
            
        return ""
