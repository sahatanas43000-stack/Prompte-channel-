import os
import json
import threading

from flask import Flask, jsonify, render_template

import bot

app = Flask(__name__)
PROMPTS_FILE = "prompts_data.json"


def get_prompt_data(prompt_id):
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(str(prompt_id))
        except Exception as e:
            print(f"[WEB] Error loading prompt data: {e}", flush=True)
    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot": "running in background thread",
    }), 200


@app.route("/prompt/<prompt_id>")
def show_prompt_page(prompt_id):
    prompt_info = get_prompt_data(prompt_id)

    smartlink = os.getenv("ADSTERRA_SMARTLINK", "#")
    popunder_script = os.getenv("ADSTERRA_POPUNDER_SCRIPT", "")

    bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")

    tg_bot_url = (
        f"https://t.me/{bot_username}?start={prompt_id}"
        if bot_username
        else "#"
    )

    if not prompt_info:
        prompt_info = {
            "title": "Prompt not found",
            "media_url": "",
            "media_type": "none",
            "prompt_text": "This prompt is no longer available.",
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


def start_bot_thread():
    thread = threading.Thread(
        target=bot.run_bot,
        daemon=True,
        name="telegram-bot",
    )
    thread.start()


# Render start.sh uses Gunicorn with 1 worker.
# Start exactly one Telegram bot thread.
start_bot_thread()
