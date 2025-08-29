import os
import logging
import sqlite3
DB_PATH = 'content_names.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS content (name TEXT PRIMARY KEY)''')
conn.commit()

def is_new_content(content_name):
    c.execute('SELECT name FROM content WHERE name=?', (content_name,))
    return c.fetchone() is None

def add_content(content_name):
    c.execute('INSERT INTO content (name) VALUES (?)', (content_name,))
    conn.commit()
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from ai import extract_content_name_ai

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
GROUP_IDS = os.getenv("GROUP_IDS", "")
TARGET_GROUP_IDS = [int(i) for i in GROUP_IDS.split()] if GROUP_IDS else []

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

for name, lg in logging.root.manager.loggerDict.items():
    if isinstance(lg, logging.Logger) and name.startswith("pyrogram"):
        lg.setLevel(logging.WARNING)        # or logging.ERROR / CRITICAL
logging.getLogger("pyrogram").setLevel(logging.WARNING)

app = Client("thumbnail_extractor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message((filters.chat(SOURCE_CHANNEL_ID)) & (filters.video | filters.document))
async def forward_and_extract(_, msg: Message) -> None:   #Triggered for every new file in the source channel.
    logger.info(f"New media in source channel: {msg.id}")
    await extract_and_broadcast(msg)

@app.on_message(filters.private & (filters.video | filters.document))
async def extract_for_private(_, msg: Message) -> None:
    logger.info(f"Video received in private chat from user: {msg.from_user.first_name}")
    await extract_and_broadcast(msg, echo_back=True)

async def extract_and_broadcast(message: Message, *, echo_back=False) -> None:

    media = message.video or message.document
    thumbs = getattr(media, "thumbs", None)

    if not thumbs:
        if echo_back:
            await message.reply_text("No thumbnail found in this file.")
        return

    try:
        thumb = thumbs[-1]                                   # largest size
        path  = await app.download_media(thumb.file_id)      # → local .jpg
        logger.info(f"Thumbnail temporarily downloaded to: {path}")
        content_name = extract_content_name_ai(message.caption or "media")
        logger.info(f"Extracted content name: {content_name}")
        caption = (
                f"🔥**NEW CONTENT ALERT**🔥\n\n"
                f"> {message.caption or 'media'}\n\n"
                f"**Search:** `{content_name}`\n\n"
                f">**Powered by:** @CharuAIbot"
        )
        if is_new_content(content_name) and not echo_back:  # Only if not received via PM and new content
            add_content(content_name)
            # 1️⃣  Post to mandatory channel
            await app.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=path,
                caption=caption,
                parse_mode=ParseMode.DEFAULT
            )

            # 2️⃣  Post to each optional group
            for gid in TARGET_GROUP_IDS:
                await app.send_photo(
                    chat_id=gid,
                    photo=path,
                    caption=caption,
                    parse_mode=ParseMode.DEFAULT
                )
            logger.info("Thumbnail extracted and sent successfully to TG. Also added to DB.")
   
        # 3️⃣  Echo back to sender (only for private handler)
        if echo_back:
            await message.reply_photo(photo=path, caption=caption, parse_mode=ParseMode.DEFAULT)
            await app.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=path,
                caption=caption,
                parse_mode=ParseMode.DEFAULT
            )
            logger.info("Thumbnail extracted and sent successfully to PM user.")

        os.remove(path)  # Clean up the downloaded thumbnail file
        logger.info(f"Thumbnail removed from: {path}")

    except Exception as e:
        logger.error("Thumbnail extraction failed: %s", e)
        if echo_back:
            await message.reply_text("Error extracting thumbnail.")


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("Hello! Send me a video, and I will extract its thumbnail for you.")

if __name__ == "__main__":
    logger.info("Bot started...")
    app.run()
    logger.info("Bot stopped.")
