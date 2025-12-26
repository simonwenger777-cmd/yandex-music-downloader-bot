import os
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import yt_dlp
from typing import Optional

class YandexMusicHandler:
    def __init__(self):
        # We no longer need yandex-music-python or a token
        pass

    async def get_track_info(self, url: str) -> Optional[dict]:
        # Simple scraping to get title and artist
        async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                
        soup = BeautifulSoup(html, 'html.parser')
        
        # Yandex Music puts title in <title> and OpenGraph tags
        title_tag = soup.find('meta', property='og:title')
        if not title_tag:
            return None
        
        # og:title usually looks like "Track Name — Artist" or similar
        full_title = title_tag['content']
        
        # Try to find artist specifically from og:description or others
        desc_tag = soup.find('meta', property='og:description')
        artist = ""
        if desc_tag:
            artist = desc_tag['content'].split('.')[0] # Usually starts with Artist name
            
        return {
            'query': full_title,
            'title': full_title.split(' — ')[0] if ' — ' in full_title else full_title,
            'artist': full_title.split(' — ')[1] if ' — ' in full_title else artist,
            'filename': f"{full_title}.mp3".replace('/', '_').replace('\\', '_')
        }

    async def download_track(self, query: str, filename: str) -> str:
        temp_path = os.path.join('/tmp' if os.name != 'nt' else '.', filename)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_path.replace('.mp3', ''), # yt-dlp adds extension
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        def run_ydl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search on YouTube and download the first result
                ydl.download([f"ytsearch1:{query} audio"])
            return temp_path

        # Run in thread pool to not block asyncio
        return await asyncio.to_thread(run_ydl)
