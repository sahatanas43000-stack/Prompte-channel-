import os
import json
import asyncio
import threading


# =========================================================
# PYTHON 3.14 / PYROGRAM COMPATIBILITY
# =========================================================

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


from flask import Flask, jsonify, render_template

import bot


app = Flask(__name__)

PROMPTS_FILE = "prompts_data.json"


# =========================================================
# PROMPT DATA
# =========================================================

def get_prompt_data(prompt_id):
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data.get(str(prompt_id))

        except Exception as e:
            print(
                f"[WEB] Error loading prompt data: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )

    return None


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "prompte-channel",
    }), 200


# =========================================================
# PROMPT PAGE
# =========================================================

@app.route("/prompt/<prompt_id>")
def show_prompt_page(prompt_id):

    prompt_info = get_prompt_data(prompt_id)

    smartlink = os.getenv(
        "ADSTERRA_SMARTLINK",
        "#"
    )

    popunder_script = os.getenv(
        "ADSTERRA_POPUNDER_SCRIPT",
        ""
    )

    bot_username = os.getenv(
        "BOT_USERNAME",
        ""
    ).strip().lstrip("@")

    if bot_username:

        tg_bot_url = (
            f"https://t.me/"
            f"{bot_username}"
            f"?start={prompt_id}"
        )

    else:

        tg_bot_url = "#"


    if not prompt_info:

        prompt_info = {
            "title": "Prompt not found",
            "media_url": "",
            "media_type": "none",
            "prompt_text": (
                "This prompt is no longer available."
            ),
        }


    return render_template(
        "prompt.html",

        prompt=prompt_info,

        prompt_id=prompt_id,

        smartlink=smartlink,

        popunder_script=popunder_script,

        tg_bot_url=tg_bot_url,

        bot_username=bot_username,
    )


# =========================================================
# START TELEGRAM BOT
# =========================================================

def start_bot_thread():

    def bot_worker():

        try:

            print(
                "[MAIN] Starting Telegram bot thread...",
                flush=True,
            )

            bot.run_bot()

        except Exception as e:

            print(
                f"[MAIN] Telegram bot crashed: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )


    thread = threading.Thread(
        target=bot_worker,
        daemon=True,
        name="telegram-bot",
    )

    thread.start()


# =========================================================
# START BOT
# =========================================================

start_bot_thread()
