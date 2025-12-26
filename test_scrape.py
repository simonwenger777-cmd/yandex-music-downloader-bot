import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_scrape(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            html = await resp.text()
            
    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.find('meta', property='og:title')
    print(f"OG Title Object: {title_tag}")
    if title_tag:
        print(f"Content: {title_tag.get('content')}")
    else:
        # Check <title> tag
        print(f"Title tag: {soup.title}")

url = "https://music.yandex.ru/track/146343467?utm_source=web&utm_medium=copy_link"
asyncio.run(test_scrape(url))
