import telebot
import datetime
import schedule
import time
import threading
import requests
import os

API_KEY = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(API_KEY)

SUBSCRIBERS_FILE = "subscribers.txt"

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_subscriber(chat_id):
    subscribers = load_subscribers()
    if str(chat_id) not in subscribers:
        with open(SUBSCRIBERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def get_weather():
    try:
        response = requests.get("https://wttr.in/Tallinn?format=%t")
        if response.status_code == 200:
            return response.text.strip()
    except:
        return "н/д"
    return "н/д"

def send_walk_reminder():
    temp = get_weather()
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M")
    message = f"👶 Сейчас {time_str}, хорошее время для прогулки.\n🌤 Температура в Таллинне: {temp}.\nОдевайтесь легко!"

    for chat_id in load_subscribers():
        try:
            bot.send_message(chat_id, message)
        except Exception as e:
            print(f"Ошибка при отправке {chat_id}: {e}")

schedule.every().day.at("09:00").do(send_walk_reminder)
schedule.every().day.at("17:30").do(send_walk_reminder)

def schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(60)

@bot.message_handler(commands=["start"])
def start(message):
    save_subscriber(message.chat.id)
    bot.reply_to(message, "🍼 Привет! Теперь ты подписан(а) на напоминания о прогулке утром и вечером 🌤👶")

threading.Thread(target=schedule_runner, daemon=True).start()
bot.polling()
