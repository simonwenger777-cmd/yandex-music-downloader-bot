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

from fastapi import BackgroundTasks

async def process_track_download(message: types.Message, track_url: str):
    status_msg = await message.answer("🔍 Ищу трек...")
    try:
        track_info = await ym_handler.get_track_info(track_url)
        if not track_info:
            await status_msg.edit_text("❌ Не удалось найти информацию о треке.")
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
            os.remove(file_path)
        else:
            await status_msg.edit_text("❌ Ошибка при скачивании (ни на YouTube, ни на SoundCloud не нашлось).")
    except Exception as e:
        logging.error(f"Error handling link: {e}")
        await status_msg.edit_text("⚠️ Ошибка при обработке. Попробуйте еще раз.")

@dp.message(F.text.contains("music.yandex.ru/"))
async def catch_yandex_link(message: types.Message):
    # This just marks the message as handled by aiogram
    # The actual processing happens in the background via FastAPI
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # No yandex handler init needed
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    update = types.Update.model_validate(data, context={"bot": bot})
    
    # Check if this is a message with a Yandex link to process in background
    if update.message and update.message.text and "music.yandex.ru/" in update.message.text:
        background_tasks.add_task(process_track_download, update.message, update.message.text)
        return {"ok": True}

    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    # Use polling for local testing if needed, but the structure is for Webhooks
    # To run locally with polling, you'd usually comment out FastAPI and use dp.start_polling(bot)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
