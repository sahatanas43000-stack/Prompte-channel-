import os
import json
import asyncio
import threading
import hashlib
import time
import re

import requests

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# CONFIG
# ============================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@NextGen_AI_Creates"
).strip()

RENDER_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://prompte-channel.onrender.com"
).strip().rstrip("/")

PROMPTS_FILE = "prompts_data.json"
POSTED_FILE = "posted_prompts.json"


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(message, flush=True)


# ============================================================
# JSON HELPERS
# ============================================================

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
            f"[JSON] Failed loading {filename}: "
            f"{type(e).__name__}: {e}"
        )
        return default


def save_json(filename, data):
    temp_file = f"{filename}.tmp"

    try:
        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            filename
        )

        return True

    except Exception as e:
        log(
            f"[JSON] Failed saving {filename}: "
            f"{type(e).__name__}: {e}"
        )

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        return False


# ============================================================
# PROMPT STORAGE
# ============================================================

def get_prompt_by_id(prompt_id):
    """
    Get EXACT prompt from prompts_data.json
    using the prompt ID from Telegram deep-link.
    """

    prompt_id = str(prompt_id).strip()

    if not prompt_id:
        return None

    data = load_json(
        PROMPTS_FILE,
        {}
    )

    if not isinstance(data, dict):
        log("[PROMPT] prompts_data.json is not a dictionary.")
        return None

    prompt = data.get(prompt_id)

    if not prompt:
        log(
            f"[PROMPT] NOT FOUND: {prompt_id}"
        )
        return None

    if not isinstance(prompt, dict):
        log(
            f"[PROMPT] Invalid data for ID: {prompt_id}"
        )
        return None

    return prompt


# ============================================================
# POSTED PROMPTS
# ============================================================

def load_posted():
    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return list(data.keys())

    return []


def save_posted(posted):
    save_json(
        POSTED_FILE,
        posted
    )


def get_prompt_fingerprint(prompt):
    raw = "|".join([
        str(prompt.get("title", "")).strip(),
        str(prompt.get("prompt_text", "")).strip(),
        str(prompt.get("media_url", "")).strip(),
        str(prompt.get("source", "")).strip(),
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def already_posted(prompt):
    fingerprint = get_prompt_fingerprint(
        prompt
    )

    posted = load_posted()

    return fingerprint in posted


def mark_posted(prompt):
    fingerprint = get_prompt_fingerprint(
        prompt
    )

    posted = load_posted()

    if fingerprint not in posted:
        posted.append(fingerprint)

    save_posted(posted)


# ============================================================
# BOT
# ============================================================

app = None


# ============================================================
# /START HANDLER
# ============================================================

async def start_handler(client, message):

    try:

        text = message.text or ""

        log(
            f"[BOT] Incoming message: {text!r}"
        )

        # ----------------------------------------------------
        # /start
        # ----------------------------------------------------

        parts = text.split(
            maxsplit=1
        )

        if len(parts) < 2:

            await message.reply_text(
                "👋 Welcome!\n\n"
                "Open a channel post and tap "
                "🔓 Get Prompt to receive the "
                "exact prompt."
            )

            return

        # ----------------------------------------------------
        # Get deep-link payload
        # Example:
        # /start ym_1790023221
        # ----------------------------------------------------

        prompt_id = parts[1].strip()

        # Remove accidental whitespace
        prompt_id = prompt_id.split()[0].strip()

        log(
            f"[BOT] Requested prompt ID: "
            f"{prompt_id}"
        )

        # ----------------------------------------------------
        # EXACT LOOKUP
        # ----------------------------------------------------

        prompt = get_prompt_by_id(
            prompt_id
        )

        if not prompt:

            await message.reply_text(
                "❌ Prompt not found.\n\n"
                f"Prompt ID: `{prompt_id}`",
                quote=True
            )

            return

        # ----------------------------------------------------
        # Get stored fields
        # ----------------------------------------------------

        title = str(
            prompt.get(
                "title",
                "AI Prompt"
            )
        ).strip()

        prompt_text = str(
            prompt.get(
                "prompt_text",
                ""
            )
        ).strip()

        # ----------------------------------------------------
        # IMPORTANT:
        # Do NOT use a generic prompt if prompt_text is empty.
        # ----------------------------------------------------

        if not prompt_text:

            log(
                f"[BOT] EMPTY PROMPT TEXT: "
                f"{prompt_id}"
            )

            await message.reply_text(
                "❌ This prompt does not contain "
                "a stored prompt text."
            )

            return

        # ----------------------------------------------------
        # Send EXACT stored prompt
        # ----------------------------------------------------

        response = (
            f"✨ {title}\n\n"
            f"{prompt_text}"
        )

        await message.reply_text(
            response,
            quote=True
        )

        log(
            f"[BOT] SUCCESS - sent stored prompt: "
            f"{prompt_id}"
        )

    except Exception as e:

        log(
            f"[BOT] /start ERROR: "
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# IMAGE URL EXTRACTION
# ============================================================

def extract_image_from_html(html):

    patterns = [

        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image',

        r'<img[^>]+src=["\']([^"\']+)',
        r'<img[^>]+data-src=["\']([^"\']+)',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            url = match.group(1).strip()

            if url.startswith("//"):
                url = "https:" + url

            if url.startswith("/"):
                continue

            if url.startswith("http"):
                return url

    return ""


# ============================================================
# SOURCE FETCHERS
# ============================================================

def fetch_youmind():

    url = "https://youmind.com/"

    try:

        log("[SCRAPER] Trying YouMind...")

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        log(
            f"[YOUMIND] HTTP "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        html = response.text

        image_url = extract_image_from_html(
            html
        )

        if not image_url:
            return None

        prompt_id = (
            "ym_"
            + str(int(time.time()))
        )

        return {
            "id": prompt_id,
            "title": "Creative AI Prompt",
            "prompt_text": (
                "Create a high-quality AI image "
                "using this creative prompt."
            ),
            "media_url": image_url,
            "media_type": "image",
            "source": "youmind",
        }

    except Exception as e:

        log(
            f"[YOUMIND] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


def fetch_aixplore():

    url = "https://aixplore.tech/"

    try:

        log("[SCRAPER] Trying AIXplore...")

        response = requests.get(
            url,
            timeout=30,
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

        html = response.text

        image_url = extract_image_from_html(
            html
        )

        if not image_url:
            return None

        prompt_id = (
            "ax_"
            + str(int(time.time()))
        )

        return {
            "id": prompt_id,
            "title": "Creative AI Prompt",
            "prompt_text": (
                "Create a cinematic AI image "
                "with professional lighting."
            ),
            "media_url": image_url,
            "media_type": "image",
            "source": "aixplore",
        }

    except Exception as e:

        log(
            f"[AIXPLORE] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


def fetch_magggic():

    url = "https://magggic.com/"

    try:

        log("[SCRAPER] Trying Magggic...")

        response = requests.get(
            url,
            timeout=30,
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

        html = response.text

        image_url = extract_image_from_html(
            html
        )

        if not image_url:
            return None

        prompt_id = (
            "mg_"
            + str(int(time.time()))
        )

        return {
            "id": prompt_id,
            "title": "Creative AI Prompt",
            "prompt_text": (
                "Generate a detailed and creative AI image."
            ),
            "media_url": image_url,
            "media_type": "image",
            "source": "magggic",
        }

    except Exception as e:

        log(
            f"[MAGGGIC] ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return None


# ============================================================
# GET NEXT PROMPT
# ============================================================

def get_next_prompt():

    fetchers = [
        fetch_youmind,
        fetch_aixplore,
        fetch_magggic,
    ]

    for fetcher in fetchers:

        try:

            prompt = fetcher()

            if not prompt:
                continue

            # Save BEFORE posting
            save_prompt(
                prompt
            )

            if already_posted(prompt):

                log(
                    "[POST] Duplicate detected, "
                    "trying next source..."
                )

                continue

            return prompt

        except Exception as e:

            log(
                f"[SCRAPER] "
                f"{fetcher.__name__} ERROR: "
                f"{type(e).__name__}: {e}"
            )

    return None


# ============================================================
# SAVE PROMPT
# ============================================================

def save_prompt(prompt):

    prompt_id = str(
        prompt.get("id", "")
    ).strip()

    if not prompt_id:
        return

    data = load_json(
        PROMPTS_FILE,
        {}
    )

    if not isinstance(data, dict):
        data = {}

    data[prompt_id] = prompt

    save_json(
        PROMPTS_FILE,
        data
    )

    log(
        f"[PROMPT] Saved: {prompt_id}"
    )


# ============================================================
# POST TO CHANNEL
# ============================================================

async def check_and_post():

    log(
        "[POST] Starting channel post check..."
    )

    prompt = get_next_prompt()

    if not prompt:

        log(
            "[POST] No NEW prompt available."
        )

        return

    prompt_id = str(
        prompt.get(
            "id",
            ""
        )
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

    # --------------------------------------------------------
    # Landing page
    # --------------------------------------------------------

    landing_url = (
        f"{RENDER_EXTERNAL_URL}"
        f"/prompt/{prompt_id}"
    )

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
        f"[POST] Prompt ID: "
        f"{prompt_id}"
    )

    log(
        f"[POST] Landing URL: "
        f"{landing_url}"
    )

    try:

        if media_url:

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


# ============================================================
# SCHEDULER
# ============================================================

async def scheduler():

    log(
        "[SCHEDULER] Started."
    )

    # First check after bot starts
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

        # 10 minutes
        await asyncio.sleep(
            600
        )


# ============================================================
# BOT MAIN
# ============================================================

async def bot_main():

    global app

    log(
        "[BOT] Creating Telegram client..."
    )

    app = Client(
        "prompte_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Register handler on THIS client/event loop.
    # --------------------------------------------------------

    app.add_handler(
        __import__(
            "pyrogram.handlers",
            fromlist=["MessageHandler"]
        ).MessageHandler(
            start_handler,
            filters.command(
                "start"
            )
        )
    )

    log(
        "[BOT] Starting Telegram client..."
    )

    await app.start()

    me = await app.get_me()

    log(
        f"[BOT] CONNECTED successfully "
        f"as @{me.username} "
        f"(ID: {me.id})"
    )

    log(
        "[BOT] Bot is running and "
        "waiting for Telegram messages."
    )

    # --------------------------------------------------------
    # Run scheduler in same event loop
    # --------------------------------------------------------

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

        await app.stop()


# ============================================================
# RUN BOT
# ============================================================

def run_bot():

    log(
        "[BOT] Creating Telegram event loop..."
    )

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(
        loop
    )

    try:

        loop.run_until_complete(
            bot_main()
        )

    except Exception as e:

        log(
            f"[BOT] FATAL ERROR: "
            f"{type(e).__name__}: {e}"
        )

    finally:

        try:
            loop.close()
        except Exception:
            pass


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    run_bot()
