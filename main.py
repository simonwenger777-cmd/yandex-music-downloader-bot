import os
import asyncio
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

from fastapi import BackgroundTasks

async def process_track_download(chat_id: int, track_url: str, status_msg_id: int):
    try:
        logging.info(f"Background task started for track: {track_url}")
        track_info = await ym_handler.get_track_info(track_url)
        if not track_info:
            await bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="❌ Не удалось найти информацию о треке.")
            return

        await bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"📥 Скачиваю: {track_info['artist']} - {track_info['title']}...")
        
        file_path = await ym_handler.download_track(track_info['query'], track_info['filename'])
        
        if file_path and os.path.exists(file_path):
            audio = FSInputFile(file_path, filename=track_info['filename'])
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=track_info['title'],
                performer=track_info['artist']
            )
            await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            os.remove(file_path)
            logging.info(f"Track sent successfully: {track_info['query']}")
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="❌ Ошибка при скачивании (не найдено на YouTube/SoundCloud).")
            logging.error(f"Download failed for query: {track_info['query']}")
    except Exception as e:
        logging.error(f"Error in background task: {e}")
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="⚠️ Ошибка при обработке. Попробуйте еще раз.")
        except:
            pass

@dp.message(F.text.contains("music.yandex.ru/"))
async def catch_yandex_link(message: types.Message):
    # This handler is a fallback in case the webhook 'if' doesn't catch it
    # We will handle it here instead of in the webhook for better aiogram integration
    status_msg = await message.answer("🔍 Ищу трек...")
    # Add to background task to free up the webhook
    # Note: Using FastAPI background tasks here is tricky since we are inside aiogram
    # But we can use asyncio.create_task for fire-and-forget
    asyncio.create_task(process_track_download(message.chat.id, message.text, status_msg.message_id))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # No yandex handler init needed
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Yandex Music Bot is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    data = await request.json()
    logging.info(f"Update received: {data}")
    update = types.Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    # Use polling for local testing if needed, but the structure is for Webhooks
    # To run locally with polling, you'd usually comment out FastAPI and use dp.start_polling(bot)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
