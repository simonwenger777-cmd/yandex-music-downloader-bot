import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv

from logic import YandexMusicHandler

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = f"/bot/{API_TOKEN}"
BASE_URL = WEBHOOK_URL

# Logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
ym_handler = YandexMusicHandler() # No token needed

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на трек из Яндекс Музыки, и я скачаю его для тебя.")

@dp.message(F.text.contains("music.yandex.ru/"))
async def handle_yandex_link(message: types.Message):
    status_msg = await message.answer("🔍 Ищу трек...")
    
    try:
        track_info = await ym_handler.get_track_info(message.text)
        if not track_info:
            await status_msg.edit_text("❌ Не удалось найти трек по этой ссылке.")
            return

        await status_msg.edit_text(f"📥 Скачиваю: {track_info['artist']} - {track_info['title']}...")
        
        file_path = await ym_handler.download_track(track_info['query'], track_info['filename'])
        
        if file_path and os.path.exists(file_path):
            audio = FSInputFile(file_path, filename=track_info['filename'])
            await bot.send_audio(
                chat_id=message.chat.id,
                audio=audio,
                title=track_info['title'],
                performer=track_info['artist']
            )
            await status_msg.delete()
            # Clean up
            os.remove(file_path)
        else:
            await status_msg.edit_text("❌ Ошибка при скачивании файла.")
    except Exception as e:
        logging.error(f"Error handling link: {e}")
        await status_msg.edit_text("⚠️ Произошла ошибка при обработке запроса.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # No yandex handler init needed
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)

if __name__ == "__main__":
    import uvicorn
    # Use polling for local testing if needed, but the structure is for Webhooks
    # To run locally with polling, you'd usually comment out FastAPI and use dp.start_polling(bot)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
