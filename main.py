import time
from languages import languages
import requests.exceptions

from database2 import database as db
from botrequests import *
from config import bot


def get_user_name(user):
    result = user.first_name
    if user.last_name:
        result += user.last_name
    return result


def get_locale(language_code: str) -> str:
    if language_code not in languages.keys():
        return 'en'
    return language_code


@bot.message_handler(commands=['start'])
def start(message):
    username = get_user_name(message.from_user)
    language = get_locale(message.from_user.language_code)
    text = languages[language]
    if not db.check_user(message.from_user.id):
        db.insert_user(user_id=message.from_user.id, name=username, language=language)
        bot.send_message(message.chat.id, f"{text['hello_1']}, {username}!\n{text['hello_2']}")
        help_command(message)
    else:
        bot.send_message(message.chat.id, f"{username}, {text['already_start']}.")


@bot.message_handler(commands=['help'])
def help_command(message):
    language = get_locale(message.from_user.language_code)
    text = languages[language]
    if db.check_user(message.from_user.id):
        bot.send_message(message.chat.id, text['help'])
    else:
        bot.send_message(message.chat.id, text['for_start'])


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal', 'history'])
def commands(message):
    language = get_locale(message.from_user.language_code)
    text = languages[language]
    command = message.text[1:]
    if not db.check_user(message.from_user.id):
        bot.send_message(message.chat.id, text['for_start'])
        return
    db.set_user_data(message.from_user.id, 'lang', language)
    last_command = db.get_user_data(user_id=message.from_user.id, col='command')
    if last_command == 'start':
        dialogs.Stages.instances[command].start(message)
    else:
        bot.send_message(message.chat.id, f"{text['already_comm']} {last_command}")
        dialogs.Stages.instances[last_command].resume(message)


@bot.message_handler(content_types='text')
def other(message):
    language = get_locale(message.from_user.language_code)
    text = languages[language]
    if not db.check_user(message.from_user.id):
        bot.send_message(message.chat.id, text['for_start'])
        return
    else:
        last_command = db.get_user_data(user_id=message.from_user.id, col='command')
        if last_command != 'start':
            dialogs.Stages.instances[last_command].resume(message)
            return
        bot.send_message(message.chat.id, text['for_help'])


while True:
    try:
        bot.polling(none_stop=True, interval=0)
    except requests.ReadTimeout:
        time.sleep(5)
    except requests.ConnectionError:
        time.sleep(120)
