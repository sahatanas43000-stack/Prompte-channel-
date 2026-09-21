import asyncio
import json
import os
import random
import re
import threading
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import requests

# Load Environment Variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

app = Client(
    "prompt_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN
)

PROMPTS_FILE = "prompts_data.json"
POSTED_FILE = "posted_prompts.json"


def load_json(filepath):
  if os.path.exists(filepath):
    try:
      with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_json(filepath, data):
  with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


# 1. YouMind Scraper Engine
def fetch_youmind():
  url = "https://youmind.com/prompts"
  headers = {
      "RSC": "1",
      "User-Agent": (
          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/127.0.0.0 Safari/537.36"
      ),
  }
  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      images = re.findall(
          r"https://3a%2f%2fcdn-assets\.youmind\.com%2fmedia%2f[^\"\s]+",
          res.text,
      )
      if not images:
        images = re.findall(
            r"https://cdn-assets\.youmind\.com/media/[^\"\s]+", res.text
        )

      if images:
        clean_img = images[0].replace("3a%2f%2f", "").replace("%2f", "/")
        return {
            "id": f"ym_{int(time.time())}",
            "title": "YouMind AI Art Prompt",
            "prompt_text": (
                "Cinematic photo, 8k resolution, highly detailed AI prompt"
                " from YouMind."
            ),
            "media_url": clean_img,
            "media_type": "photo",
        }
  except Exception as e:
    print(f"YouMind Scraper Error: {e}")
  return None


# 2. AiXplore Scraper Engine
def fetch_aixplore():
  url = "https://aixplore.in/prompts"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
      )
  }
  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      images = re.findall(
          r'https://aixplore\.in/uploads/[^"\s\']+\.(?:jpg|png|webp)', res.text
      )
      if images:
        return {
            "id": f"aix_{int(time.time())}",
            "title": "AiXplore Creative Prompt",
            "prompt_text": (
                "Ultra realistic portrait, 35mm photography style prompt from"
                " AiXplore."
            ),
            "media_url": images[0],
            "media_type": "photo",
        }
  except Exception as e:
    print(f"AiXplore Scraper Error: {e}")
  return None


# 3. Magggic Scraper Engine
def fetch_magggic():
  url = "https://magggic.com/explore"
  headers = {
      "RSC": "1",
      "User-Agent": (
          "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
      ),
  }
  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      images = re.findall(
          r'https://[^"\s\']+\.(?:jpg|png|webp|mp4)', res.text
      )
      valid_images = [
          img
          for img in images
          if "magggic" in img or "cdn" in img or "media" in img
      ]
      if valid_images:
        media_url = valid_images[0]
        media_type = "video" if media_url.endswith(".mp4") else "photo"
        return {
            "id": f"mg_{int(time.time())}",
            "title": "Magggic AI Prompt",
            "prompt_text": (
                "Creative AI artwork with vibrant colors and lighting from"
                " Magggic."
            ),
            "media_url": media_url,
            "media_type": media_type,
        }
  except Exception as e:
    print(f"Magggic Scraper Error: {e}")
  return None


def get_next_prompt():
  sources = [fetch_youmind, fetch_aixplore, fetch_magggic]
  random.shuffle(sources)

  for fetcher in sources:
    data = fetcher()
    if data:
      return data
  return None


def check_and_post():
  prompt_data = get_next_prompt()
  if not prompt_data:
    print("No new prompt found from any source.")
    return

  posted_data = load_json(POSTED_FILE)
  if prompt_data["id"] in posted_data:
    return

  all_prompts = load_json(PROMPTS_FILE)
  all_prompts[prompt_data["id"]] = prompt_data
  save_json(PROMPTS_FILE, all_prompts)

  landing_url = f"{RENDER_EXTERNAL_URL}/prompt/{prompt_data['id']}"
  reply_markup = InlineKeyboardMarkup([[
      InlineKeyboardButton("🔘 Get Prompt & Resources", url=landing_url)
  ]])

  caption = (
      f"🔥 **{prompt_data['title']}**\n\nClick the button below to view and"
      " download the full prompt."
  )

  try:
    if prompt_data["media_type"] == "video":
      app.send_video(
          chat_id=CHANNEL_USERNAME,
          video=prompt_data["media_url"],
          caption=caption,
          reply_markup=reply_markup,
      )
    else:
      app.send_photo(
          chat_id=CHANNEL_USERNAME,
          photo=prompt_data["media_url"],
          caption=caption,
          reply_markup=reply_markup,
      )

    posted_data[prompt_data["id"]] = True
    save_json(POSTED_FILE, posted_data)
    print(f"Successfully posted {prompt_data['id']} to channel!")
  except Exception as e:
    print(f"Failed to post on Telegram Channel: {e}")


@app.on_message(filters.command("start"))
def start_handler(client, message):
  args = message.text.split()
  if len(args) > 1:
    prompt_id = args[1]
    all_prompts = load_json(PROMPTS_FILE)
    prompt_info = all_prompts.get(prompt_id)

    if prompt_info:
      caption = (
          f"✨ **Full Prompt Text:**\n\n`{prompt_info['prompt_text']}`"
      )
      try:
        if prompt_info.get("media_type") == "video":
          client.send_video(
              chat_id=message.chat.id,
              video=prompt_info["media_url"],
              caption=caption,
          )
        else:
          client.send_photo(
              chat_id=message.chat.id,
              photo=prompt_info["media_url"],
              caption=caption,
          )
        return
      except Exception:
        client.send_message(
            chat_id=message.chat.id,
            text=f"✨ **Full Prompt Text:**\n\n`{prompt_info['prompt_text']}`",
        )
        return

  message.reply_text(
      "Welcome! Use the buttons in our channel posts to get exclusive AI"
      " prompts."
  )


def auto_post_loop():
  # Wait 10 seconds after bot starts before making the first post
  time.sleep(10)
  while True:
    try:
      check_and_post()
    except Exception as e:
      print(f"Loop Exception: {e}")
    time.sleep(1800)  # Runs every 30 minutes


def run_bot():
  try:
    loop = asyncio.get_event_loop()
  except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

  print("Multi-Source AI Bot standard engine running...")

  # Start auto-posting in a separate background thread
  threading.Thread(target=auto_post_loop, daemon=True).start()

  # Run Pyrogram natively so events and commands work properly
  app.run()
