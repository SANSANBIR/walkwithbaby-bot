import telebot
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz
import threading
import random
import json
import os
from datetime import datetime
import time
# Telegram Bot Token from environment variable
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:raise RuntimeError("TELEGRAM_BOT_TOKEN env variable not set")
bot = telebot.TeleBot(TOKEN)
# Load subscribers data from JSON file
subscribers = {}
subscribers_file = 'subscribers.json'
if os.path.exists(subscribers_file):
try:with open(subscribers_file, 'r') as f:
subscribers = json.load(f)
except json.JSONDecodeError:
subscribers = {}
else:# Create an empty JSON file if it doesn't exist with open(subscribers_file, 'w') as f:json.dump(subscribers, f)
# Function to save subscribers data to JSON file
def save_subscribers():
    with open(subscribers_file, 'w') as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=4)
# List of positive affirmations for each supported language
affirmations = {
    'en': [
        "You are a wonderful mother.",
        "You are doing an amazing job.",
        "Your love and care make all the difference.",
        "You are exactly what your child needs.",
        "Your best is enough.",
        "You are strong, capable, and loving."],
    'ru': [
        "Ты замечательная мама.",
        "Ты делаешь потрясающую работу.",
        "Твоя любовь и забота очень много значат.",
        "Ты именно та мама, которая нужна твоему ребенку.",
        "Ты делаешь всё, что в твоих силах, и этого достаточно.",
        "Ты сильная, способная и любящая мама."
    ],
    'es': [
        "Eres una madre maravillosa.",
        "Estás haciendo un trabajo increíble.",
        "Tu amor y cuidado marcan la diferencia.",
        "Eres exactamente lo que tus hijos necesitan.",
        "Tu mejor esfuerzo es suficiente.",
        "Eres fuerte, capaz y amorosa."
    ]
}
# Temporary data for users in setup process (for language and city steps)
user_setup_steps = {}

# Command handler for /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.chat.id)
    if user_id in subscribers:
        # User is already subscribed
        lang = subscribers[user_id].get('language', 'en')
        responses = {
            'en': "You are already subscribed to daily affirmations.",
            'ru': "Вы уже подписаны на ежедневные аффирмации.",
            'es': "Ya estás suscrito a las afirmaciones diarias."
        }
        bot.send_message(message.chat.id, responses.get(lang, responses['en']))
    else:
        # New user: initiate setup by asking for language
        welcome_text = ("Welcome to WalkWithBaby Bot!\n"
                        "Please choose your language / "
                        "Пожалуйста, выберите язык / "
                        "Por favor, elige tu idioma:\n"
                        "English (en) / Русский (ru) / Español (es)")
        bot.send_message(message.chat.id, welcome_text)
        # Save state that next step is language selection
        user_setup_steps[user_id] = {'step': 'language'}
# Handler for text messages (to capture language and city inputs during setup and language change)
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_text(message):
    user_id = str(message.chat.id)
    # Check if user is in the middle of setup or language change process
    if user_id in user_setup_steps:
        step = user_setup_steps[user_id].get('step')
        if step == 'language':
            # Process language selection
            lang_input = message.text.strip().lower()
            # Map common inputs to language code
            if lang_input in ['english', 'en', 'английский', 'англ', 'англ.']:
                chosen_lang = 'en'
            elif lang_input in ['русский', 'руский', 'ru', 'rus', 'russian']:
                chosen_lang = 'ru'
            elif lang_input in ['español', 'espanol', 'es', 'spanish', 'esp']:
                chosen_lang = 'es'
            else:
                # Unrecognized language input
                retry_text = ("Language not recognized. Please type 'en', 'ru', or 'es'.\n"
                              "Не удалось распознать язык. Пожалуйста, введите en, ru или es.\n"
                              "No se reconoció el idioma. Por favor ingrese en, ru o es.")
                bot.send_message(message.chat.id, retry_text)
                return
            # Store chosen language and ask for city next
            user_setup_steps[user_id]['language'] = chosen_lang
            user_setup_steps[user_id]['step'] = 'city'
            prompts = {
                'en': "Great! Now send me your city (e.g., London):",
                'ru': "Отлично! Теперь отправьте мне название вашего города (например, Москва):",
                'es': "¡Genial! Ahora envíame el nombre de tu ciudad (por ejemplo, Madrid):"
            }
            bot.send_message(message.chat.id, prompts[chosen_lang])
            return
        elif step == 'city':
            # Process city input
            chosen_lang = user_setup_steps[user_id].get('language', 'en')
            city_name = message.text.strip()
            # Use geopy to get coordinates of the city
            geolocator = Nominatim(user_agent="walkwithbaby_bot")
            try:
                location = geolocator.geocode(city_name)
            except Exception as e:
                # Geocoding service error (e.g., connection issue)
                error_msgs = {
                    'en': "I couldn't find that city due to a service error. Please try again.",
                    'ru': "Не удалось найти этот город из-за ошибки сервиса. Пожалуйста, попробуйте еще раз.",
                    'es': "No pude encontrar esa ciudad debido a un error de servicio. Por favor, inténtalo de nuevo."
                }
                bot.send_message(message.chat.id, error_msgs.get(chosen_lang, error_msgs['en']))
                return
            if location is None:
                # City not found
                not_found_msgs = {
                    'en': "City not found. Please double-check the spelling and try again:",
                    'ru': "Город не найден. Пожалуйста, проверьте написание и попробуйте снова:",
                    'es': "Ciudad no encontrada. Por favor revisa la ortografía e inténtalo de nuevo:"
                }
                bot.send_message(message.chat.id, not_found_msgs.get(chosen_lang, not_found_msgs['en']))
                return
            # Get timezone using timezonefinder
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            if timezone_str is None:
                # If timezone could not be determined
                tz_error_msgs = {
                    'en': "Could not determine the timezone for this location. Please try a different city.",
                    'ru': "Не удалось определить часовой пояс для этого места. Пожалуйста, попробуйте другой город.",
                    'es': "No se pudo determinar la zona horaria de esta ubicación. Por favor intenta con otra ciudad."
                }
                bot.send_message(message.chat.id, tz_error_msgs.get(chosen_lang, tz_error_msgs['en']))
                return
            # Save subscriber data
            subscribers[user_id] = {
                'city': city_name,
                'timezone': timezone_str,
                'language': chosen_lang
            }
            save_subscribers()
            # Confirmation message
            confirm_msgs = {
                'en': f"Setup complete! City set to {city_name}, language set to English.\n"
                      f"You will receive daily affirmations at 20:00 your local time.\n"
                      f"Use /stop to unsubscribe or /language to change language.",
                'ru': f"Настройка завершена! Город: {city_name}, язык: русский.\n"
                      f"Вы будете получать ежедневные аффирмации в 20:00 по вашему времени.\n"
                      f"Используйте /stop для отписки или /language для смены языка.",
                'es': f"¡Configuración completa! Ciudad: {city_name}, idioma: español.\n"
                      f"Recibirás afirmaciones diarias a las 20:00 hora local.\n"
                      f"Usa /stop para darte de baja o /language para cambiar el idioma."
            }
            bot.send_message(message.chat.id, confirm_msgs.get(chosen_lang, confirm_msgs['en']))
            # Remove from temp setup state
            user_setup_steps.pop(user_id, None)
            return
        elif step == 'language_change':
            # Process language change selection
            lang_input = message.text.strip().lower()
            if lang_input in ['english', 'en', 'английский', 'англ', 'англ.']:
                new_lang = 'en'
            elif lang_input in ['русский', 'руский', 'ru', 'rus', 'russian']:
                new_lang = 'ru'
            elif lang_input in ['español', 'espanol', 'es', 'spanish', 'esp']:
                new_lang = 'es'
            else:
                # Unrecognized language input
                retry_text = {
                    'en': "Language not recognized. Please enter en, ru, or es:",
                    'ru': "Язык не распознан. Пожалуйста, введите en, ru или es:",
                    'es': "Idioma no reconocido. Por favor ingresa en, ru o es:"
                }
                # Use user's current language for retry prompt if available
                current_lang = subscribers.get(user_id, {}).get('language', 'en')
                bot.send_message(message.chat.id, retry_text.get(current_lang, retry_text['en']))
                return
            # Update language in subscribers data
            subscribers[user_id]['language'] = new_lang
            save_subscribers()
            # Confirmation message in the new language
            confirm_msgs = {
                'en': "Language has been changed to English.",
                'ru': "Язык был изменен на русский.",
                'es': "El idioma ha sido cambiado a español."
            }
            bot.send_message(message.chat.id, confirm_msgs.get(new_lang, confirm_msgs['en']))
            # Clear the user from setup steps
            user_setup_steps.pop(user_id, None)
            return
# Command handler for /stop to unsubscribe
@bot.message_handler(commands=['stop'])
def handle_stop(message):
    user_id = str(message.chat.id)
    if user_id not in subscribers:
        # If user is not subscribed
        bot.send_message(message.chat.id, "You are not subscribed.")
    else:
        lang = subscribers[user_id].get('language', 'en')
        stop_msgs = {
            'en': "You have been unsubscribed from daily affirmations. Send /start to subscribe again anytime.",
            'ru': "Вы отписаны от ежедневных аффирмаций. Отправьте /start, чтобы подписаться снова в любое время.",
            'es': "Has cancelado la suscripción a las afirmaciones diarias. Envía /start para suscribirte nuevamente cuando quieras."
        }
        bot.send_message(message.chat.id, stop_msgs.get(lang, stop_msgs['en']))
        # Remove from subscribers
        subscribers.pop(user_id, None)
        save_subscribers()
# Command handler for /language to change language
@bot.message_handler(commands=['language'])
def handle_language(message):
    user_id = str(message.chat.id)
    if user_id not in subscribers:
        # User not subscribed yet
        bot.send_message(message.chat.id, "Use /start to set up your subscription first.")
    else:
        lang = subscribers[user_id].get('language', 'en')
        prompts = {
            'en': "Choose a new language: English (en) / Русский (ru) / Español (es)",
            'ru': "Выберите новый язык: English (en) / Русский (ru) / Español (es)",
            'es': "Elige un nuevo idioma: English (en) / Русский (ru) / Español (es)"
        }
        bot.send_message(message.chat.id, prompts.get(lang, prompts['en']))
        # Set state to language change
        user_setup_steps[user_id] = {'step': 'language_change'}
# Background thread to send daily affirmations at 20:00 local time for each user
def schedule_affirmations():
    while True:
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        for user_id, data in list(subscribers.items()):
            try:
                tz = pytz.timezone(data['timezone'])
            except Exception:
                # If timezone is invalid or not found
                continue
            now_local = now_utc.astimezone(tz)
            if now_local.hour == 20 and now_local.minute == 0:
                today_str = str(now_local.date())
                if data.get('last_sent') != today_str:
                    lang = data.get('language', 'en')
                    affirmation = random.choice(affirmations.get(lang, affirmations['en']))
                    try:
                        bot.send_message(int(user_id), affirmation)
                        # Mark that we sent today to avoid duplicate sends
                        subscribers[user_id]['last_sent'] = today_str
                        save_subscribers()
                    except Exception as e:
                        # If the user has blocked the bot or another send error occurred, remove user
                        if "Forbidden" in str(e) or "blocked" in str(e):
                            subscribers.pop(user_id, None)
                            save_subscribers()
        # Wait 60 seconds before checking again
        time.sleep(60)
# Start the scheduler thread
scheduler_thread = threading.Thread(target=schedule_affirmations, daemon=True)
scheduler_thread.start()
# Start the bot polling loop (to handle incoming messages)
bot.polling(none_stop=True)
