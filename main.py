import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile, LabeledPrice, PreCheckoutQuery, Message
from aiogram.filters import Command
from dotenv import load_dotenv

from logic import YandexMusicHandler
import database

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
ym_handler = YandexMusicHandler()
download_queue = asyncio.Queue()

# Queue Worker
async def download_worker():
    logging.info("👷 Queue worker started")
    while True:
        chat_id, track_url, status_msg_id, user_id = await download_queue.get()
        try:
            await process_track_download(chat_id, track_url, status_msg_id)
        except Exception as e:
            logging.error(f"Error in worker: {e}")
        finally:
            download_queue.task_done()

async def process_track_download(chat_id: int, track_url: str, status_msg_id: int):
    try:
        logging.info(f"Processing track: {track_url}")
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

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await database.get_user(message.from_user.id, message.from_user.username)
    await message.reply(
        "Привет! Пришли мне ссылку на трек из Яндекс Музыки.\n\n"
        "💎 Условия:\n"
        "- Первое скачивание бесплатно!\n"
        "- Далее — 3 звезды за трек.\n"
        "- Для exsslx и polya_poela — безлимит! 😎"
    )

@dp.message(F.text.contains("music.yandex.ru/"))
async def catch_yandex_link(message: types.Message):
    user = await database.get_user(message.from_user.id, message.from_user.username)
    
    # Check limits
    if not user['is_whitelisted'] and user['free_downloads'] <= 0:
        # Prompt for payment
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Скачивание трека",
            description="Оплата 1 скачивания (3 звезды)",
            payload=f"download_{message.text}", # Pass URL in payload
            provider_token="", # Empty for Stars
            currency="XTR",
            prices=[LabeledPrice(label="Скачивание", amount=3)]
        )
        return

    # Decrement free if applicable
    if not user['is_whitelisted']:
        await database.decrement_free_download(message.from_user.id)

    status_msg = await message.answer("⏳ Добавлено в очередь...")
    await download_queue.put((message.chat.id, message.text, status_msg.message_id, message.from_user.id))

@dp.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("download_"):
        track_url = payload.replace("download_", "")
        status_msg = await message.answer("✅ Оплата прошла! Добавляю в очередь...")
        await download_queue.put((message.chat.id, track_url, status_msg.message_id, message.from_user.id))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    # Log configuration for debugging
    webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    logging.info(f"🚀 Starting bot...")
    logging.info(f"PORT: {os.getenv('PORT', '10000')}")
    logging.info(f"WEBHOOK_URL: {webhook_url}")
    logging.info(f"BOT_TOKEN (masked): {API_TOKEN[:5] if API_TOKEN else 'None'}...")
    
    if not API_TOKEN or not WEBHOOK_URL:
        logging.error("❌ CRITICAL: BOT_TOKEN or WEBHOOK_URL is missing!")
    
    try:
        await bot.set_webhook(webhook_url)
        logging.info("⭐ Webhook set successfully")
    except Exception as e:
        logging.error(f"❌ Failed to set webhook: {e}")
    
    # Start worker
    worker_task = asyncio.create_task(download_worker())
        
    yield
    logging.info("👋 Shutting down bot...")
    worker_task.cancel()
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "ok", "message": "Yandex Music Bot is running"}

@app.api_route("/health", methods=["GET", "HEAD"])
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
    uvicorn.run(app, host="0.0.0.0", port=10000)
