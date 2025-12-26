import asyncio
import aiohttp
import json

async def check_oembed():
    # Test oEmbed endpoint
    track_url = "https://music.yandex.ru/track/146343467"
    oembed_url = f"https://music.yandex.ru/handlers/oembed-json.jsx?url={track_url}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print(f"Testing oEmbed: {oembed_url}")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(oembed_url) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                try:
                    text = await resp.text()
                    print(f"Raw: {text}")
                    data = json.loads(text)
                    print(f"Keys: {data.keys()}")
                except Exception as e:
                    print(f"JSON Error: {e}")
                    print(await resp.text())

asyncio.run(check_oembed())
