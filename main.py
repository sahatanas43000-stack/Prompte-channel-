import asyncio
import json
import os
import threading

# Python 3.14 Fix: Pyrogram import করার আগেই MainThread-এ Event Loop সেট করতে হবে
try:
  loop = asyncio.get_event_loop()
except RuntimeError:
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)

from flask import Flask, jsonify, redirect, render_template, request
import bot  # Bot logic import

app = Flask(__name__)

PROMPTS_FILE = 'prompts_data.json'


def get_prompt_data(prompt_id):
  if os.path.exists(PROMPTS_FILE):
    try:
      with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get(str(prompt_id))
    except Exception as e:
      print(f'Error loading prompt data: {e}')
  return None


@app.route('/')
def home():
  return render_template('index.html')


@app.route('/health')
def health():
  return jsonify({'status': 'ok', 'bot_status': 'active'}), 200


@app.route('/prompt/<prompt_id>')
def show_prompt_page(prompt_id):
  prompt_info = get_prompt_data(prompt_id)

  smartlink = os.getenv('ADSTERRA_SMARTLINK', '#')
  popunder_script = os.getenv('ADSTERRA_POPUNDER_SCRIPT', '')

  bot_username = os.getenv('BOT_USERNAME', '').replace('@', '')
  tg_bot_url = (
      f'https://t.me/{bot_username}?start={prompt_id}' if bot_username else '#'
  )

  if not prompt_info:
    prompt_info = {
        'title': 'Exclusive AI Prompt',
        'media_url': (
            'https://via.placeholder.com/600x400?text=AI+Media+Preview'
        ),
        'media_type': 'photo',
    }

  return render_template(
      'prompt.html',
      prompt=prompt_info,
      prompt_id=prompt_id,
      smartlink=smartlink,
      popunder_script=popunder_script,
      tg_bot_url=tg_bot_url,
  )


# Start Background Bot Thread
threading.Thread(target=bot.run_bot, daemon=True).start()

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
