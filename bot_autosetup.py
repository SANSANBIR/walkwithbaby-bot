import telebot
import os
import json
import datetime
import threading
import time
import requests
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from pytz import timezone, utc

API_KEY = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(API_KEY)
SUBSCRIBERS_FILE = "subscribers.json"

geolocator = Nominatim(user_agent="walkwithbaby-bot")
tf = TimezoneFinder()

LANGS = {
    "ru": {
        "welcome": "👶 Добро пожаловать!\n\n📍 Напиши, из какого ты города?",
        "ask_lang": "🗣️ На каком языке тебе удобно общаться? (русский / english / español)",
        "saved": "✅ Всё настроено! Язык — русский, город — {city}",
        "affirm": ["💖 Ты хорошая мама. Ты всё успеваешь.", "🌸 Ты заботишься о себе и малыше — это уже много."]
    },
    "en": {
        "welcome": "👶 Welcome!\n\n📍 Please tell me your city.",
        "ask_lang": "🗣️ What language would you like to use? (english / русский / español)",
        "saved": "✅ All set! Language: English, City: {city}",
        "affirm": ["💖 You are a great mom. You’re doing enough.", "🌸 You’re caring and that’s more than enough."]
    },
    "es": {
        "welcome": "👶 ¡Bienvenida!\n\n📍 Dime de qué ciudad eres.",
        "ask_lang": "🗣️ ¿En qué idioma deseas usar el bot? (español / русский / english)",
        "saved": "✅ ¡Listo! Idioma: español, Ciudad: {city}",
        "affirm": ["💖 Eres una gran mamá. Estás haciendo lo suficiente.", "🌸 Cuidas y amas, y eso ya es mucho."]
    }
}

def load_data():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {}
    with open(SUBSCRIBERS_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f)

def get_timezone(city):
    try:
        location = geolocator.geocode(city)
        if location:
            return tf.timezone_at(lng=location.longitude, lat=location.latitude)
    except:
        return None

def set_user(chat_id, city, lang):
    data = load_data()
    tz = get_timezone(city) or "Europe/Tallinn"
    data[str(chat_id)] = {"city": city, "lang": lang, "timezone": tz}
    save_data(data)

def get_user(chat_id):
    return load_data().get(str(chat_id))

def detect_lang(text):
    text = text.lower()
    if "english" in text:
        return "en"
    elif "español" in text:
        return "es"
    elif "русский" in text:
        return "ru"
    return None

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    if get_user(chat_id):
        return
    bot.send_message(chat_id, "👶 Welcome! / Добро пожаловать! / ¡Bienvenida!\n\n🌍 Please tell me your city / Напиши город / Dime tu ciudad")

@bot.message_handler(func=lambda m: not get_user(m.chat.id))
def first_steps(message):
    chat_id = message.chat.id
    data = load_data()
    uid = str(chat_id)

    if uid not in data:
        data[uid] = {"step": "awaiting_city"}
        save_data(data)
        bot.send_message(chat_id, LANGS["ru"]["ask_lang"] + "\n" + LANGS["en"]["ask_lang"] + "\n" + LANGS["es"]["ask_lang"])
        return

    if data[uid].get("step") == "awaiting_city":
        data[uid]["city"] = message.text.strip()
        data[uid]["step"] = "awaiting_lang"
        save_data(data)
        return

    if data[uid].get("step") == "awaiting_lang":
        lang = detect_lang(message.text)
        if not lang:
            bot.send_message(chat_id, "❗ Please reply: русский / english / español")
            return
        city = data[uid].get("city", "Tallinn")
        set_user(chat_id, city, lang)
        bot.send_message(chat_id, LANGS[lang]["saved"].format(city=city))

def send_affirmations():
    while True:
        now_utc = datetime.datetime.now(tz=utc)
        users = load_data()
        for uid, info in users.items():
            tzname = info.get("timezone", "Europe/Tallinn")
            local_time = now_utc.astimezone(timezone(tzname))
            if local_time.strftime("%H:%M") == "20:00":
                lang = info.get("lang", "ru")
                affirm = LANGS[lang]["affirm"]
                try:
                    bot.send_message(int(uid), random.choice(affirm))
                except:
                    pass
        time.sleep(60)

# Запускаем аффирмации в фоновом режиме
threading.Thread(target=send_affirmations, daemon=True).start()
bot.polling()
