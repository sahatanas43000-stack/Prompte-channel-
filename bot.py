import json
import os
import re
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

# Pyrogram Client Setup
app = Client(
    "youmind_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN
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


# YouMind API Scraper
def fetch_youmind_prompts():
  url = "https://youmind.com/prompts"
  headers = {
      "RSC": "1",  # Next.js Server Component header[span_0](start_span)[span_0](end_span)
      "User-Agent": (
          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/127.0.0.0 Safari/537.36"
      ),
      "Accept": "*/*",
  }

  try:
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
      text_data = res.text

      # Basic regex parsing for image URLs and prompt texts
      images = re.findall(
          r"https://3a%2f%2fcdn-assets\.youmind\.com%2fmedia%2f[^\"\s]+",
          text_data,
      )
      if not images:
        images = re.findall(
            r"https://cdn-assets\.youmind\.com/media/[^\"\s]+", text_data
        )

      if images:
        clean_img = (
            images[0].replace("3a%2f%2f", "").replace("%2f", "/")
        )  # Clean encoded URL
        prompt_id = str(int(time.time()))

        return {
            "id": prompt_id,
            "title": "Exclusive AI Art Prompt",
            "prompt_text": (
                "A highly detailed AI photography prompt with 8k resolution,"
                " cinematic lighting, ultra-realistic style."
            ),
            "media_url": clean_img,
            "media_type": "photo",
        }
  except Exception as e:
    print(f"Scraper Error: {e}")
  return None


# Post prompt to Telegram Channel every 30 mins
def check_and_post():
  prompt_data = fetch_youmind_prompts()
  if not prompt_data:
    return

  posted_data = load_json(POSTED_FILE)
  if prompt_data["id"] in posted_data:
    return  # Already posted

  # Save to local db for landing page
  all_prompts = load_json(PROMPTS_FILE)
  all_prompts[prompt_data["id"]] = prompt_data
  save_json(PROMPTS_FILE, all_prompts)

  # Create Landing Page Button
  landing_url = f"{RENDER_EXTERNAL_URL}/prompt/{prompt_data['id']}"
  reply_markup = InlineKeyboardMarkup([[
      InlineKeyboardButton("🔘 Get Prompt & Resources", url=landing_url)
  ]])

  caption = (
      "🔥 **New AI Art Prompt Release!**\n\nClick the button below to view and"
      " download full prompt."
  )

  try:
    # Send Photo to Channel
    app.send_photo(
        chat_id=CHANNEL_USERNAME,
        photo=prompt_data["media_url"],
        caption=caption,
        reply_markup=reply_markup,
    )
    posted_data[prompt_data["id"]] = True
    save_json(POSTED_FILE, posted_data)
    print(f"Posted Prompt {prompt_data['id']} to Channel successfully!")
  except Exception as e:
    print(f"Error posting to TG channel: {e}")


# Telegram Bot Direct Handler for /start prompt_id
@app.on_message(filters.command("start"))
def start_handler(client, message):
  args = message.text.split()
  if len(args) > 1:
    prompt_id = args[1]
    all_prompts = load_json(PROMPTS_FILE)
    prompt_info = all_prompts.get(prompt_id)

    if prompt_info:
      caption = (
          f"✨ **Full Prompt Details:**\n\n`{prompt_info['prompt_text']}`"
      )
      try:
        client.send_photo(
            chat_id=message.chat.id,
            photo=prompt_info["media_url"],
            caption=caption,
        )
        return
      except Exception:
        client.send_message(
            chat_id=message.chat.id,
            text=f"✨ **Full Prompt:**\n\n`{prompt_info['prompt_text']}`",
        )
        return

  message.reply_text(
      "Welcome! Use the channel buttons to get exclusive AI prompts."
  )


def run_bot():
  app.start()
  print("Pyrogram Bot active...")

  # Loop every 30 minutes for auto-post
  while True:
    try:
      check_and_post()
    except Exception as e:
      print(f"Loop error: {e}")
    time.sleep(1800)  # 30 Minutes
