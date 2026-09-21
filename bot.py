import os
import json
import asyncio
import random
import time
import re
from urllib.parse import urljoin

import requests

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler


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
    ""
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
# LOGGING
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
# JSON HELPERS
# =========================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        log(
            f"[JSON] Failed reading {filename}: "
            f"{type(e).__name__}: {e}"
        )
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        return True

    except Exception as e:
        log(
            f"[JSON] Failed writing {filename}: "
            f"{type(e).__name__}: {e}"
        )
        return False


# =========================================================
# POSTED PROMPTS
# =========================================================

def load_posted():
    data = load_json(POSTED_FILE, [])

    if not isinstance(data, list):
        return []

    return data


def mark_posted(prompt_id):
    posted = load_posted()

    if prompt_id not in posted:
        posted.append(prompt_id)

    save_json(POSTED_FILE, posted)


# =========================================================
# PROMPT DATA
# =========================================================

def save_prompt(prompt):
    if not prompt:
        return False

    prompt_id = str(prompt.get("id", "")).strip()

    if not prompt_id:
        return False

    data = load_json(PROMPTS_FILE, {})

    if not isinstance(data, dict):
        data = {}

    data[prompt_id] = prompt

    return save_json(PROMPTS_FILE, data)


# =========================================================
# URL / IMAGE HELPERS
# =========================================================

def absolute_url(base_url, value):
    if not value:
        return ""

    value = value.strip()

    if value.startswith("//"):
        return "https:" + value

    return urljoin(base_url, value)


def extract_image(html, base_url=""):
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
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
# YOUMIND SCRAPER
# =========================================================

def fetch_youmind():
    log("[SCRAPER] Trying YouMind...")

    try:
        url = "https://youmind.com/"

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/140 Safari/537.36"
                )
            }
        )

        log(
            f"[YOUMIND] HTTP {response.status_code}"
        )

        if response.status_code != 200:
            return None

        html = response.text

        image_url = extract_image(
            html,
            url
        )

        prompt_id = f"ym_{int(time.time())}"

        prompt = {
            "id": prompt_id,
            "title": "AI Prompt",
            "prompt_text": (
                "Create a high-quality AI image "
                "using this creative prompt."
            ),
            "media_url": image_url,
            "media_type": "image" if image_url else "none",
            "source": "YouMind",
        }

        log(
            f"[SCRAPER] SUCCESS from YouMind: "
            f"{prompt_id}"
        )

        return prompt

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
            f"[AIXPLORE] HTTP {response.status_code}"
        )

        if response.status_code != 200:
            return None

        image_url = extract_image(
            response.text,
            url
        )

        prompt_id = f"ax_{int(time.time())}"

        return {
            "id": prompt_id,
            "title": "AI Prompt",
            "prompt_text": (
                "Create a cinematic AI image "
                "with professional lighting."
            ),
            "media_url": image_url,
            "media_type": "image" if image_url else "none",
            "source": "AIXplore",
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
            f"[MAGGGIC] HTTP {response.status_code}"
        )

        if response.status_code != 200:
            return None

        image_url = extract_image(
            response.text,
            url
        )

        prompt_id = f"mg_{int(time.time())}"

        return {
            "id": prompt_id,
            "title": "Creative AI Prompt",
            "prompt_text": (
                "Generate a detailed and "
                "creative AI image."
            ),
            "media_url": image_url,
            "media_type": "image" if image_url else "none",
            "source": "Magggic",
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
    prompt_id = f"fallback_{int(time.time())}"

    return {
        "id": prompt_id,
        "title": "AI Image Prompt",
        "prompt_text": (
            "A cinematic portrait of a young person "
            "standing in a dramatic urban environment, "
            "soft natural lighting, realistic details, "
            "professional photography, 35mm film look."
        ),
        "media_url": "",
        "media_type": "none",
        "source": "Fallback",
    }


# =========================================================
# GET NEXT PROMPT
# =========================================================

def get_next_prompt():
    scrapers = [
        fetch_youmind,
        fetch_aixplore,
        fetch_magggic,
    ]

    random.shuffle(scrapers)

    for scraper in scrapers:

        prompt = scraper()

        if not prompt:
            continue

        prompt_id = str(
            prompt.get("id", "")
        )

        if prompt_id in load_posted():
            continue

        save_prompt(prompt)

        return prompt

    log("[SCRAPER] All sources failed. Using fallback.")

    prompt = create_fallback_prompt()

    save_prompt(prompt)

    return prompt


# =========================================================
# TELEGRAM START HANDLER
# =========================================================

async def start_handler(client, message):

    try:
        text = message.text or ""

        parts = text.split(maxsplit=1)

        prompt_id = ""

        if len(parts) > 1:
            prompt_id = parts[1].strip()

        data = load_json(
            PROMPTS_FILE,
            {}
        )

        prompt = data.get(prompt_id)

        if not prompt:

            await message.reply_text(
                "❌ Prompt not found."
            )

            return

        prompt_text = prompt.get(
            "prompt_text",
            "Prompt unavailable."
        )

        await message.reply_text(
            f"✨ {prompt.get('title', 'AI Prompt')}\n\n"
            f"{prompt_text}"
        )

    except Exception as e:

        log(
            f"[BOT] /start ERROR: "
            f"{type(e).__name__}: {e}"
        )

        try:
            await message.reply_text(
                "❌ Something went wrong."
            )
        except Exception:
            pass


# =========================================================
# CHANNEL POST
# =========================================================

async def check_and_post():
    log("[POST] Starting channel post check...")

    prompt = get_next_prompt()

    if not prompt:
        log("[POST] No prompt available.")
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

    caption = (
        f"✨ {title}\n\n"
        f"{prompt_text}\n\n"
        f"🔗 Get Prompt"
    )

    log(
        f"[POST] Sending to "
        f"{CHANNEL_USERNAME}..."
    )

    try:

        # IMPORTANT:
        # This await happens on the SAME event loop
        # where the Pyrogram client was created.

        if media_url:

            await app.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=media_url,
                caption=caption
            )

        else:

            await app.send_message(
                chat_id=CHANNEL_USERNAME,
                text=caption
            )

        mark_posted(prompt_id)

        log(
            f"[POST] SUCCESS: {prompt_id}"
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

    # Small delay so Telegram connection finishes.
    await asyncio.sleep(10)

    while True:

        try:

            log("[SCHEDULER] Running post check...")

            await check_and_post()

        except Exception as e:

            log(
                f"[SCHEDULER] ERROR: "
                f"{type(e).__name__}: {e}"
            )

        # Run every 10 minutes.
        await asyncio.sleep(600)


# =========================================================
# BOT MAIN
# =========================================================

async def bot_main():

    global app

    log("[BOT] Creating Telegram client...")

    app = Client(
        "prompt_bot",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    # Register handler AFTER client creation
    app.add_handler(
        MessageHandler(
            start_handler,
            filters.command("start")
        )
    )

    log("[BOT] Starting Telegram client...")

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

        # Scheduler runs on the EXACT SAME LOOP.
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

        log("[BOT] Stopping Telegram client...")

        try:
            await app.stop()
        except Exception:
            pass


# =========================================================
# RUN BOT
# =========================================================

def run_bot():

    if not check_environment():
        log("[BOT] Environment check failed.")
        return

    log("[BOT] Creating Telegram event loop...")

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:

        loop.run_until_complete(
            bot_main()
        )

    except KeyboardInterrupt:

        log("[BOT] Shutdown requested.")

    except Exception as e:

        log(
            f"[BOT] FATAL ERROR: "
            f"{type(e).__name__}: {e}"
        )

    finally:

        try:
            loop.run_until_complete(
                asyncio.sleep(0)
            )
        except Exception:
            pass

        loop.close()

        log("[BOT] Event loop closed.")
