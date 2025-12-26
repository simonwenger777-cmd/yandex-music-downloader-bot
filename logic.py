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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        print(f"Error: Yandex returned status {resp.status}")
                        return None
                    html = await resp.text()

            soup = BeautifulSoup(html, 'html.parser')
            
            # Debug: Check title
            page_title = soup.title.string if soup.title else "No title"
            print(f"Page title: {page_title}")

            full_title = None
            title_tag = soup.find('meta', property='og:title')
            
            if title_tag:
                full_title = title_tag['content']
            elif soup.title:
                # Fallback to <title> which is usually "Track - Artist. Listen online..."
                full_title = soup.title.string.replace(" — Яндекс Музыка", "")

            if not full_title:
                print("Error: Could not find title in extracting metadata")
                return None

            print(f"Extracted title: {full_title}")

            # Try to smart split
            if ' — ' in full_title:
                parts = full_title.split(' — ')
                title = parts[0]
                artist = parts[1]
            else:
                 # Try to get artist from description
                desc_tag = soup.find('meta', property='og:description')
                if desc_tag:
                    artist = desc_tag['content'].split('.')[0]
                    title = full_title
                else:
                    artist = "Unknown Artist"
                    title = full_title
            
            query = f"{artist} - {title}"
            return {
                'query': query,
                'title': title,
                'artist': artist,
                'filename': f"{artist} - {title}.mp3".replace('/', '_').replace('\\', '_')
            }
        except Exception as e:
            print(f"Exception in get_track_info: {e}")
            return None

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
