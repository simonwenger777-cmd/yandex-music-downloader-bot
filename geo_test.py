import asyncio
import aiohttp

async def check_access():
    url = "https://music.yandex.ru/track/146343467"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True) as resp:
            print(f"Initial Status: {resp.status}")
            print(f"Final URL: {resp.url}")
            text = await resp.text()
            print(f"Page Title in text: {text.split('<title>')[1].split('</title>')[0] if '<title>' in text else 'No title'}")
            
            if "Доступно в" in text or "not available" in text:
                print("GEO BLOCK DETECTED")

asyncio.run(check_access())
