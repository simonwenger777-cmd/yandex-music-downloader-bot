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
if not API_TOKEN:
    logging.error("BOT_TOKEN is not set!")
if not WEBHOOK_URL:
    logging.error("WEBHOOK_URL is not set!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
ym_handler = YandexMusicHandler()
logging.info(f"Webhook URL set to: {BASE_URL}{WEBHOOK_PATH}")

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на трек из Яндекс Музыки, и я скачаю его для тебя.")



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
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    logging.info(f"Setting webhook to: {webhook_url}")
    try:
        success = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message"]
        )
        logging.info(f"Set webhook result: {success}")
        webhook_info = await bot.get_webhook_info()
        logging.info(f"Webhook info: {webhook_info}")
    except Exception as e:
        logging.error(f"Failed to set webhook: {e}")
    yield
    logging.info("Shutting down... deleting webhook")
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def index():
    return {"status": "ok", "message": "Bot is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "webhook_configured": bool(BASE_URL and API_TOKEN)}

@app.get("/debug/webhook")
async def debug_webhook():
    try:
        info = await bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "ip_address": info.ip_address
        }
    except Exception as e:
        return {"error": str(e)}

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    try:
        data = await request.json()
        logging.info(f"Update received: {data.get('update_id')}")
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Error in webhook: {e}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use polling for local testing if needed, but the structure is for Webhooks
    # To run locally with polling, you'd usually comment out FastAPI and use dp.start_polling(bot)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
