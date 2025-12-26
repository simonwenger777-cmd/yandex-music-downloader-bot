from duckduckgo_search import DDGS
import asyncio

async def test_ddg():
    url = "https://music.yandex.ru/track/146343467"
    print(f"Searching for: {url}")
    
    try:
        results = DDGS().text(keywords=url, max_results=1)
        if results:
            print(f"Title: {results[0]['title']}")
            print(f"Body: {results[0]['body']}")
        else:
            print("No results found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ddg())
