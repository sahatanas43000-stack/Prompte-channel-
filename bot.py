import os
import json
import asyncio
import random
import time
import re
import hashlib
from urllib.parse import urljoin

import requests

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================================================
# ENV
# =========================================================

API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@NextGenAICreates"
).strip()

RENDER_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://prompte-channel.onrender.com"
).strip().rstrip("/")


# =========================================================
# FILES
# =========================================================

PROMPTS_FILE = "prompts_data.json"
POSTED_FILE = "posted_prompts.json"


# =========================================================
# GLOBALS
# =========================================================

app = None


# =========================================================
# LOG
# =========================================================

def log(message):
    print(message, flush=True)


# =========================================================
# ENV CHECK
# =========================================================

def check_environment():

    missing = []

    if not API_ID:
        missing.append("API_ID")

    if not API_HASH:
        missing.append("API_HASH")

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not CHANNEL_USERNAME:
        missing.append("CHANNEL_USERNAME")

    if missing:
        log(
            "[BOT] Missing environment variables: "
            + ", ".join(missing)
        )
        return False

    return True


# =========================================================
# JSON
# =========================================================

def load_json(filename, default):

    try:

        if not os.path.exists(filename):
            return default

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:

        log(
            f"[JSON] READ ERROR {filename}: "
            f"{type(e).__name__}: {e}"
        )

        return default


def save_json(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        return True

    except Exception as e:

        log(
            f"[JSON] WRITE ERROR {filename}: "
            f"{type(e).__name__}: {e}"
        )

        return False


# =========================================================
# POSTED DATA
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if not isinstance(data, list):
        return []

    return data


def save_posted(data):

    # Keep the file small.
    data = data[-500:]

    save_json(
        POSTED_FILE,
        data
    )


def mark_posted(prompt):

    posted = load_posted()

    prompt_id = str(
        prompt.get("id", "")
    )

    fingerprint = get_prompt_fingerprint(
        prompt
    )

    record = {
        "id": prompt_id,
        "fingerprint": fingerprint,
        "time": int(time.time())
    }

    posted.append(record)

    save_posted(posted)


def already_posted(prompt):

    posted = load_posted()

    fingerprint = get_prompt_fingerprint(
        prompt
    )

    prompt_id = str(
        prompt.get("id", "")
    )

    for item in posted:

        # Backward compatibility:
        # old file may contain only IDs.
        if isinstance(item, str):

            if item == prompt_id:
                return True

        elif isinstance(item, dict):

            if item.get("id") == prompt_id:
                return True

            if item.get("fingerprint") == fingerprint:
                return True

    return False


# =========================================================
# DUPLICATE PROTECTION
# =========================================================

def get_prompt_fingerprint(prompt):

    title = str(
        prompt.get("title", "")
    ).strip().lower()

    text = str(
        prompt.get("prompt_text", "")
    ).strip().lower()

    media = str(
        prompt.get("media_url", "")
    ).strip().lower()

    source = str(
        prompt.get("source", "")
    ).strip().lower()

    raw = "|".join([
        title,
        text,
        media,
        source
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# =========================================================
# SAVE PROMPT
# =========================================================

def save_prompt(prompt):

    if not prompt:
        return False

    prompt_id = str(
        prompt.get("id", "")
    ).strip()

    if not prompt_id:
        return False

    data = load_json(
        PROMPTS_FILE,
        {}
    )

    if not isinstance(data, dict):
        data = {}

    data[prompt_id] = prompt

    return save_json(
        PROMPTS_FILE,
        data
    )


# =========================================================
# URL
# =========================================================

def absolute_url(base_url, value):

    if not value:
        return ""

    value = value.strip()

    if value.startswith("//"):
        return "https:" + value

    return urljoin(
        base_url,
        value
    )


# =========================================================
# IMAGE EXTRACT
# =========================================================

def extract_image(html, base_url=""):

    patterns = [

        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',

        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',

        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',

        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image',

        r'<img[^>]+src=["\']([^"\']+)'

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            return absolute_url(
                base_url,
                match.group(1)
            )

    return ""


# =========================================================
# YOUMIND
# =========================================================

def fetch_youmind():

    log("[SCRAPER] Trying YouMind...")

    try:

        url = "https://youmind.com/"

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/153 Safari/537.36"
            }
        )

        log(
            f"[YOUMIND] HTTP "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        image_url = extract_image(
            response.text,
            url
        )

        prompt_id = (
            f"ym_{int(time.time())}"
        )

        return {
            "id": prompt_id,
            "title": "AI Prompt",
            "prompt_text":
                "Create a high-quality AI image "
                "using this creative prompt.",
            "media_url": image_url,
            "media_type":
                "image" if image_url else "none",
            "source": "YouMind"
        }

    except Exception as e:

        log(
            f"[YOUMIND] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# AIXPLORE
# =========================================================

def fetch_aixplore():

    log("[SCRAPER] Trying AIXplore...")

    try:

        url = "https://aixplore.app/"

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        log(
            f"[AIXPLORE] HTTP "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        image_url = extract_image(
            response.text,
            url
        )

        prompt_id = (
            f"ax_{int(time.time())}"
        )

        return {
            "id": prompt_id,
            "title": "AI Prompt",
            "prompt_text":
                "Create a cinematic AI image "
                "with professional lighting.",
            "media_url": image_url,
            "media_type":
                "image" if image_url else "none",
            "source": "AIXplore"
        }

    except Exception as e:

        log(
            f"[AIXPLORE] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# MAGGGIC
# =========================================================

def fetch_magggic():

    log("[SCRAPER] Trying Magggic...")

    try:

        url = "https://magggic.com/"

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        log(
            f"[MAGGGIC] HTTP "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        image_url = extract_image(
            response.text,
            url
        )

        prompt_id = (
            f"mg_{int(time.time())}"
        )

        return {
            "id": prompt_id,
            "title": "Creative AI Prompt",
            "prompt_text":
                "Generate a detailed and "
                "creative AI image.",
            "media_url": image_url,
            "media_type":
                "image" if image_url else "none",
            "source": "Magggic"
        }

    except Exception as e:

        log(
            f"[MAGGGIC] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# FALLBACK
# =========================================================

def create_fallback_prompt():

    prompt_id = (
        f"fallback_{int(time.time())}"
    )

    return {
        "id": prompt_id,
        "title": "AI Image Prompt",
        "prompt_text":
            "A cinematic portrait of a young person "
            "standing in a dramatic urban environment, "
            "soft natural lighting, realistic details, "
            "professional photography, 35mm film look.",
        "media_url": "",
        "media_type": "none",
        "source": "Fallback"
    }


# =========================================================
# GET UNIQUE PROMPT
# =========================================================

def get_next_prompt():

    scrapers = [
        fetch_youmind,
        fetch_aixplore,
        fetch_magggic
    ]

    random.shuffle(scrapers)

    for scraper in scrapers:

        prompt = scraper()

        if not prompt:
            continue

        if already_posted(prompt):

            log(
                "[SCRAPER] Duplicate prompt "
                "detected. Skipping."
            )

            continue

        save_prompt(prompt)

        return prompt

    log(
        "[SCRAPER] No new unique prompt found."
    )

    return None


# =========================================================
# /START
# =========================================================

async def start_handler(
    client,
    message
):

    try:

        text = message.text or ""

        parts = text.split(
            maxsplit=1
        )

        if len(parts) < 2:

            await message.reply_text(
                "👋 Send a prompt link to get "
                "the full prompt."
            )

            return

        prompt_id = parts[1].strip()

        data = load_json(
            PROMPTS_FILE,
            {}
        )

        prompt = data.get(
            prompt_id
        )

        if not prompt:

            await message.reply_text(
                "❌ Prompt not found."
            )

            return

        title = prompt.get(
            "title",
            "AI Prompt"
        )

        prompt_text = prompt.get(
            "prompt_text",
            "Prompt unavailable."
        )

        await message.reply_text(
            f"✨ {title}\n\n"
            f"{prompt_text}"
        )

    except Exception as e:

        log(
            f"[BOT] /start ERROR: "
            f"{type(e).__name__}: {e}"
        )


# =========================================================
# CHANNEL POST
# =========================================================

async def check_and_post():

    log("[POST] Starting channel post check...")

    prompt = get_next_prompt()

    if not prompt:
        log("[POST] No NEW prompt available.")
        return

    prompt_id = str(
        prompt.get("id", "")
    )

    title = prompt.get(
        "title",
        "AI Prompt"
    )

    prompt_text = prompt.get(
        "prompt_text",
        ""
    )

    media_url = prompt.get(
        "media_url",
        ""
    )

    # Landing page
    landing_url = (
        f"{RENDER_EXTERNAL_URL}"
        f"/prompt/{prompt_id}"
    )

    # Real Telegram clickable button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔓 Get Prompt",
                    url=landing_url
                )
            ]
        ]
    )

    caption = (
        f"✨ {title}\n\n"
        f"{prompt_text}\n\n"
        f"👇 Click below to get the full prompt."
    )

    log(
        f"[POST] Sending to "
        f"{CHANNEL_USERNAME}..."
    )

    log(
        f"[POST] Landing URL: "
        f"{landing_url}"
    )

    try:

        if media_url:

            # First download the image ourselves.
            # Telegram no longer needs to fetch the
            # external image URL.
            image_response = requests.get(
                media_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            image_response.raise_for_status()

            image_path = (
                f"/tmp/{prompt_id}.jpg"
            )

            with open(
                image_path,
                "wb"
            ) as f:
                f.write(
                    image_response.content
                )

            await app.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=image_path,
                caption=caption,
                reply_markup=keyboard
            )

            try:
                os.remove(image_path)
            except Exception:
                pass

        else:

            await app.send_message(
                chat_id=CHANNEL_USERNAME,
                text=caption,
                reply_markup=keyboard
            )

        mark_posted(prompt)

        log(
            f"[POST] SUCCESS: "
            f"{prompt_id}"
        )

    except Exception as e:

        log(
            f"[POST] FAILED: "
            f"{type(e).__name__}: {e}"
        )


# =========================================================
# SCHEDULER
# =========================================================

async def scheduler():

    log("[SCHEDULER] Started.")

    await asyncio.sleep(10)

    while True:

        try:

            log(
                "[SCHEDULER] Running post check..."
            )

            await check_and_post()

        except Exception as e:

            log(
                f"[SCHEDULER] ERROR: "
                f"{type(e).__name__}: {e}"
            )

        # Check every 10 minutes
        await asyncio.sleep(600)


# =========================================================
# BOT MAIN
# =========================================================

async def bot_main():

    global app

    log(
        "[BOT] Creating Telegram client..."
    )

    app = Client(
        "prompt_bot",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )

    app.add_handler(
        MessageHandler(
            start_handler,
            filters.command("start")
        )
    )

    log(
        "[BOT] Starting Telegram client..."
    )

    await app.start()

    try:

        me = await app.get_me()

        log(
            f"[BOT] CONNECTED successfully as "
            f"@{me.username} "
            f"(ID: {me.id})"
        )

        log(
            "[BOT] Bot is running and waiting "
            "for Telegram messages."
        )

        scheduler_task = asyncio.create_task(
            scheduler()
        )

        try:

            await asyncio.Event().wait()

        finally:

            scheduler_task.cancel()

            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass

    finally:

        log(
            "[BOT] Stopping Telegram client..."
        )

        try:
            await app.stop()
        except Exception:
            pass


# =========================================================
# RUN BOT
# =========================================================

def run_bot():

    if not check_environment():

        log(
            "[BOT] Environment check failed."
        )

        return

    log(
        "[BOT] Creating Telegram event loop..."
    )

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:

        loop.run_until_complete(
            bot_main()
        )

    except KeyboardInterrupt:

        log(
            "[BOT] Shutdown requested."
        )

    except Exception as e:

        log(
            f"[BOT] FATAL ERROR: "
            f"{type(e).__name__}: {e}"
        )

    finally:

        loop.close()

        log(
            "[BOT] Event loop closed."
        )
