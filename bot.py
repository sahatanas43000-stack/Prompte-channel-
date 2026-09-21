import asyncio
import json
import os
import random
import re
import time

import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")


PROMPTS_FILE = "prompts_data.json"
POSTED_FILE = "posted_prompts.json"


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

def check_environment():
    required = {
        "API_ID": API_ID,
        "API_HASH": API_HASH,
        "BOT_TOKEN": BOT_TOKEN,
        "CHANNEL_USERNAME": CHANNEL_USERNAME,
        "RENDER_EXTERNAL_URL": RENDER_EXTERNAL_URL,
    }

    missing = [
        key for key, value in required.items()
        if not value
    ]

    if missing:
        print(
            "[BOT] ERROR: Missing environment variables: "
            + ", ".join(missing),
            flush=True,
        )
        return False

    return True


# =========================================================
# PYROGRAM CLIENT
# =========================================================

app = Client(
    "prompt_bot",
    api_id=int(API_ID) if API_ID else None,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception as e:
        print(
            f"[JSON] Failed to load {filepath}: {type(e).__name__}: {e}",
            flush=True,
        )
        return {}


def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(
            f"[JSON] Failed to save {filepath}: {type(e).__name__}: {e}",
            flush=True,
        )


# =========================================================
# URL / IMAGE HELPERS
# =========================================================

def clean_url(url):
    if not url:
        return None

    url = url.strip()
    url = url.replace("\\/", "/")
    url = url.replace("&amp;", "&")

    return url


def extract_image_urls(html):
    """
    Try several common image formats:
    - og:image
    - twitter:image
    - normal img src
    - direct image URLs
    """

    found = []

    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'https?://[^"\'>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\'>\s]*)?',
    ]

    for pattern in patterns:
        try:
            matches = re.findall(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            for item in matches:
                item = clean_url(item)

                if item and item not in found:
                    found.append(item)

        except Exception:
            continue

    return found


# =========================================================
# 1. YOUMIND
# =========================================================

def fetch_youmind():
    url = "https://youmind.com/prompts"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/127.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        res = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        print(
            f"[YOUMIND] HTTP {res.status_code}",
            flush=True,
        )

        if res.status_code != 200:
            return None

        images = extract_image_urls(res.text)

        # Keep YouMind-related URLs first
        images = [
            img for img in images
            if "youmind" in img.lower()
            or "cdn" in img.lower()
        ] or images

        if images:
            return {
                "id": f"ym_{int(time.time())}",
                "title": "YouMind AI Art Prompt",
                "prompt_text": (
                    "Cinematic photo, 8k resolution, highly detailed "
                    "AI prompt inspired by modern AI artwork."
                ),
                "media_url": images[0],
                "media_type": "photo",
            }

    except Exception as e:
        print(
            f"[YOUMIND] ERROR: {type(e).__name__}: {e}",
            flush=True,
        )

    return None


# =========================================================
# 2. AIXPLORE
# =========================================================

def fetch_aixplore():
    url = "https://aixplore.in/prompts"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/127.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        res = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        print(
            f"[AIXPLORE] HTTP {res.status_code}",
            flush=True,
        )

        if res.status_code != 200:
            return None

        images = extract_image_urls(res.text)

        images = [
            img for img in images
            if "aixplore" in img.lower()
            or "upload" in img.lower()
        ] or images

        if images:
            return {
                "id": f"aix_{int(time.time())}",
                "title": "AiXplore Creative Prompt",
                "prompt_text": (
                    "Ultra realistic portrait, cinematic lighting, "
                    "35mm photography style, highly detailed."
                ),
                "media_url": images[0],
                "media_type": "photo",
            }

    except Exception as e:
        print(
            f"[AIXPLORE] ERROR: {type(e).__name__}: {e}",
            flush=True,
        )

    return None


# =========================================================
# 3. MAGGGIC
# =========================================================

def fetch_magggic():
    url = "https://magggic.com/explore"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/127.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        res = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        print(
            f"[MAGGGIC] HTTP {res.status_code}",
            flush=True,
        )

        if res.status_code != 200:
            return None

        images = extract_image_urls(res.text)

        images = [
            img for img in images
            if (
                "magggic" in img.lower()
                or "cdn" in img.lower()
                or "media" in img.lower()
            )
        ] or images

        if images:
            media_url = images[0]

            media_type = (
                "video"
                if re.search(
                    r"\.(mp4|mov|webm)(?:\?|$)",
                    media_url,
                    re.IGNORECASE,
                )
                else "photo"
            )

            return {
                "id": f"mg_{int(time.time())}",
                "title": "Magggic AI Prompt",
                "prompt_text": (
                    "Creative AI artwork with cinematic lighting, "
                    "vibrant colors and highly detailed composition."
                ),
                "media_url": media_url,
                "media_type": media_type,
            }

    except Exception as e:
        print(
            f"[MAGGGIC] ERROR: {type(e).__name__}: {e}",
            flush=True,
        )

    return None


# =========================================================
# FALLBACK PROMPT
# =========================================================

def create_fallback_prompt():
    """
    Used only when all external sources fail.
    This lets us test Telegram channel posting independently
    from the external scraper websites.
    """

    timestamp = int(time.time())

    return {
        "id": f"local_{timestamp}",
        "title": "AI Portrait Prompt",
        "prompt_text": (
            "Create a cinematic ultra-realistic portrait of a young "
            "South Asian man, natural facial features, realistic skin "
            "texture, soft cinematic lighting, 35mm photography, "
            "shallow depth of field, highly detailed, 8K."
        ),
        "media_url": None,
        "media_type": "text",
    }


# =========================================================
# GET NEXT PROMPT
# =========================================================

def get_next_prompt():
    sources = [
        ("YouMind", fetch_youmind),
        ("AiXplore", fetch_aixplore),
        ("Magggic", fetch_magggic),
    ]

    random.shuffle(sources)

    for name, fetcher in sources:
        print(
            f"[SCRAPER] Trying {name}...",
            flush=True,
        )

        data = fetcher()

        if data:
            print(
                f"[SCRAPER] SUCCESS from {name}: {data['id']}",
                flush=True,
            )
            return data

        print(
            f"[SCRAPER] No usable result from {name}",
            flush=True,
        )

    print(
        "[SCRAPER] All external sources failed.",
        flush=True,
    )

    # Important: create local test prompt
    return create_fallback_prompt()


# =========================================================
# POST TO TELEGRAM CHANNEL
# =========================================================

def check_and_post():
    print(
        "[POST] Starting channel post check...",
        flush=True,
    )

    if not CHANNEL_USERNAME:
        print(
            "[POST] ERROR: CHANNEL_USERNAME is missing.",
            flush=True,
        )
        return

    if not RENDER_EXTERNAL_URL:
        print(
            "[POST] ERROR: RENDER_EXTERNAL_URL is missing.",
            flush=True,
        )
        return

    prompt_data = get_next_prompt()

    if not prompt_data:
        print(
            "[POST] No prompt available.",
            flush=True,
        )
        return

    posted_data = load_json(POSTED_FILE)

    if prompt_data["id"] in posted_data:
        print(
            f"[POST] Already posted: {prompt_data['id']}",
            flush=True,
        )
        return

    # Save prompt first
    all_prompts = load_json(PROMPTS_FILE)

    all_prompts[prompt_data["id"]] = prompt_data

    save_json(
        PROMPTS_FILE,
        all_prompts,
    )

    landing_url = (
        f"{RENDER_EXTERNAL_URL.rstrip('/')}"
        f"/prompt/{prompt_data['id']}"
    )

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔘 Get Prompt & Resources",
                    url=landing_url,
                )
            ]
        ]
    )

    caption = (
        f"🔥 **{prompt_data['title']}**\n\n"
        "Click the button below to view and "
        "download the full prompt."
    )

    try:
        print(
            f"[POST] Sending to {CHANNEL_USERNAME}...",
            flush=True,
        )

        if (
            prompt_data["media_type"] == "video"
            and prompt_data.get("media_url")
        ):
            app.send_video(
                chat_id=CHANNEL_USERNAME,
                video=prompt_data["media_url"],
                caption=caption,
                reply_markup=reply_markup,
            )

        elif (
            prompt_data["media_type"] == "photo"
            and prompt_data.get("media_url")
        ):
            app.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=prompt_data["media_url"],
                caption=caption,
                reply_markup=reply_markup,
            )

        else:
            # Fallback/local prompt
            app.send_message(
                chat_id=CHANNEL_USERNAME,
                text=(
                    f"🔥 **{prompt_data['title']}**\n\n"
                    f"{prompt_data['prompt_text']}\n\n"
                    "👇 Get the full prompt:"
                ),
                reply_markup=reply_markup,
            )

        posted_data[prompt_data["id"]] = True

        save_json(
            POSTED_FILE,
            posted_data,
        )

        print(
            f"[POST] SUCCESS: {prompt_data['id']} "
            f"-> {CHANNEL_USERNAME}",
            flush=True,
        )

    except Exception as e:
        print(
            f"[POST] FAILED: {type(e).__name__}: {e}",
            flush=True,
        )


# =========================================================
# TELEGRAM /start HANDLER
# =========================================================

@app.on_message(filters.command("start"))
def start_handler(client, message):
    print(
        f"[BOT] /start received from "
        f"{message.from_user.id if message.from_user else 'unknown'}",
        flush=True,
    )

    args = message.text.split()

    if len(args) > 1:
        prompt_id = args[1]

        all_prompts = load_json(PROMPTS_FILE)
        prompt_info = all_prompts.get(prompt_id)

        if prompt_info:
            prompt_text = prompt_info.get(
                "prompt_text",
                "Prompt text unavailable.",
            )

            caption = (
                "✨ **Full Prompt Text:**\n\n"
                f"`{prompt_text}`"
            )

            try:
                if (
                    prompt_info.get("media_type") == "video"
                    and prompt_info.get("media_url")
                ):
                    client.send_video(
                        chat_id=message.chat.id,
                        video=prompt_info["media_url"],
                        caption=caption,
                    )

                elif (
                    prompt_info.get("media_type") == "photo"
                    and prompt_info.get("media_url")
                ):
                    client.send_photo(
                        chat_id=message.chat.id,
                        photo=prompt_info["media_url"],
                        caption=caption,
                    )

                else:
                    client.send_message(
                        chat_id=message.chat.id,
                        text=caption,
                    )

                print(
                    f"[BOT] Prompt sent successfully: {prompt_id}",
                    flush=True,
                )

                return

            except Exception as e:
                print(
                    f"[BOT] Reply media failed: "
                    f"{type(e).__name__}: {e}",
                    flush=True,
                )

                try:
                    client.send_message(
                        chat_id=message.chat.id,
                        text=caption,
                    )

                    print(
                        "[BOT] Text fallback reply sent.",
                        flush=True,
                    )

                except Exception as e2:
                    print(
                        f"[BOT] Text fallback also failed: "
                        f"{type(e2).__name__}: {e2}",
                        flush=True,
                    )

                return

    try:
        message.reply_text(
            "Welcome! Use the buttons in our channel posts "
            "to get AI prompts."
        )

    except Exception as e:
        print(
            f"[BOT] Welcome reply failed: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )


# =========================================================
# BOT MAIN
# =========================================================

async def bot_main():

    print(
        "[BOT] Starting Telegram client...",
        flush=True,
    )

    if not check_environment():
        raise RuntimeError(
            "Required environment variables are missing."
        )

    try:
        await app.start()

        me = await app.get_me()

        print(
            f"[BOT] CONNECTED successfully as "
            f"@{me.username or me.first_name} "
            f"(ID: {me.id})",
            flush=True,
        )

    except Exception as e:
        print(
            f"[BOT] CONNECTION FAILED: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )
        raise

    # -----------------------------------------------------
    # Auto posting task
    # -----------------------------------------------------

    async def auto_post_task():

        print(
            "[SCHEDULER] Started.",
            flush=True,
        )

        # First test after 10 seconds
        await asyncio.sleep(10)

        while True:

            try:
                print(
                    "[SCHEDULER] Running post check...",
                    flush=True,
                )

                loop = asyncio.get_running_loop()

                await loop.run_in_executor(
                    None,
                    check_and_post,
                )

            except Exception as e:
                print(
                    f"[SCHEDULER] ERROR: "
                    f"{type(e).__name__}: {e}",
                    flush=True,
                )

            # 30 minutes
            await asyncio.sleep(1800)

    asyncio.create_task(
        auto_post_task()
    )

    print(
        "[BOT] Bot is running and waiting for Telegram messages.",
        flush=True,
    )

    await asyncio.Event().wait()


# =========================================================
# RUN BOT
# =========================================================

def run_bot():

    print(
        "[BOT] Creating Telegram event loop...",
        flush=True,
    )

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            bot_main()
        )

    except Exception as e:
        print(
            f"[BOT] FATAL ERROR: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

    finally:
        try:
            loop.close()
        except Exception:
            pass
