import asyncio
from yandex_music import ClientAsync

async def test_lib():
    try:
        client = ClientAsync()
        await client.init()
        print("Init successful without token")
        
        # Try to get track
        track_id = '146343467'
        tracks = await client.tracks([track_id])
        if tracks:
            print(f"Found track: {tracks[0].title} - {tracks[0].artists[0].name}")
        else:
            print("Track not found")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_lib())
