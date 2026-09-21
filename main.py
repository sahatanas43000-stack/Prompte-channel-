import os
import json
import threading
from flask import Flask, render_template, request, redirect, jsonify
import bot  # Imports our bot logic

app = Flask(__name__)

# Load local prompt data store
PROMPTS_FILE = 'prompts_data.json'

def get_prompt_data(prompt_id):
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(str(prompt_id))
        except Exception as e:
            print(f"Error loading prompt data: {e}")
    return None

@app.route('/')
def home():
    return "Bot and Landing Page Server is Running Live!"

# Health check route for UptimeRobot
@app.route('/health')
def health():
    return jsonify({"status": "ok", "bot_status": "active"}), 200

# Dynamic Landing Page Route for TG Channel Users
@app.route('/prompt/<prompt_id>')
def show_prompt_page(prompt_id):
    prompt_info = get_prompt_data(prompt_id)
    
    # Adsterra variables from Environment
    smartlink = os.getenv("ADSTERRA_SMARTLINK", "#")
    popunder_script = os.getenv("ADSTERRA_POPUNDER_SCRIPT", "")
    
    bot_username = os.getenv("BOT_USERNAME", "").replace("@", "")
    tg_bot_url = f"https://t.me/{bot_username}?start={prompt_id}" if bot_username else "#"

    if not prompt_info:
        # Fallback dummy data if ID not found
        prompt_info = {
            "title": "Exclusive AI Prompt",
            "media_url": "https://via.placeholder.com/600x400?text=AI+Media+Preview",
            "media_type": "image"
        }

    return render_template(
        'prompt.html',
        prompt=prompt_info,
        prompt_id=prompt_id,
        smartlink=smartlink,
        popunder_script=popunder_script,
        tg_bot_url=tg_bot_url
    )

def start_bot_thread():
    print("Starting Background Telegram Bot...")
    bot.run_bot()

# Run Pyrogram bot in background thread when Flask starts
threading.Thread(target=start_bot_thread, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
