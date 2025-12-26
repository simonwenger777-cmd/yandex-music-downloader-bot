import asyncio
import aiohttp
import json

async def check_handlers():
    track_id = "146343467"
    url = f"https://music.yandex.ru/handlers/track.jsx?track={track_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://music.yandex.ru/',
        'X-Retpath-Y': 'https://music.yandex.ru/',
    }
    
    print(f"Testing Handlers: {url}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                text = await resp.text()
                try:
                    data = json.loads(text)
                    # Track info is usually in 'track' or root
                    track = data.get('track', {})
                    print(f"Title: {track.get('title')}")
                    artists = [a.get('name') for a in track.get('artists', [])]
                    print(f"Artists: {artists}")
                except Exception as e:
                    print(f"JSON Error: {e}")
                    print(f"Raw start: {text[:100]}")

asyncio.run(check_handlers())
