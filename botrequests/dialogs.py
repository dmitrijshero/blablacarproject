import time
from datetime import datetime, timedelta
from languages import languages
from telebot import types
from telegram_bot_calendar import WMonthTelegramCalendar

from database2 import database as db
import hotels
from config import bot, log_file_name


class Stages:
    instances = {}

    def __init__(self, command: str, script: list, search_method=''):
        self.__command = command
        Stages.instances[command] = self
        self.__script = script
        self.__search_method = search_method

    def write_log(self, message, log_text=None):
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file_name, 'a', encoding='utf-8') as log_file:
            if log_text is None:
                log_text = f'{current_time}\tПользователь {message.chat.id}.\t Выполняется команда {self.__command}. ' \
                           f'Сообщение пользователя: {message.text}\n'
            log_file.write(log_text)

    def go_to_next_stage(self, message):
        self.write_log(message=message)
        stage = db.get_user_data(user_id=message.chat.id, col='stage')
        stage += 1
        db.set_user_data(user_id=message.chat.id, col='stage', data=stage)
        self.__script[stage - 1](message)

    def start(self, message):
        stage = 1
        db.set_user_data(user_id=message.chat.id, col='stage', data=stage)
        db.set_user_data(user_id=message.from_user.id, col='command', data=self.__command)
        if self.__command != 'history':
            db.history_start_command(user_id=message.chat.id)
        self.__script[stage - 1](message)

    def resume(self, message):
        stage = db.get_user_data(user_id=message.chat.id, col='stage')
        self.__script[stage - 1](message)

    def get_search_method(self) -> str:
        return self.__search_method

    def stop_current_command(self, message) -> None:
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        self.write_log(message=message, log_text=f'{current_time}\t Пользователь {message.chat.id} прервал '
                                                 f'выполнение команды {self.__command}.')
        db.set_user_data(user_id=message.from_user.id, col='command', data='start')
        db.set_user_data(user_id=message.chat.id, col='stage', data='0')


def location_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    message = bot.send_message(message.chat.id, text['city_search'])
    bot.register_next_step_handler(message, from_location_stage)


def from_location_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    search_string = message.text
    locations = hotels.get_location(search_string)
    if len(locations) == 0:
        bot.send_message(user_id, text['city_not_found'])
        location_stage(message)
        return
    keys = types.InlineKeyboardMarkup(row_width=1)
    for location in locations:
        keys.add(types.InlineKeyboardButton(text=location['city'], callback_data=f"search{location['location_id']}"))
    keys.add(types.InlineKeyboardButton(text=text['cancel'], callback_data='city'))
    db.set_user_data(user_id=user_id, col='search', data=locations)
    bot.send_message(user_id, text['select'], reply_markup=keys)
        

@bot.callback_query_handler(func=lambda call: call.data.startswith('search'))
def apply_city(call: types.CallbackQuery):
    user_id = call.from_user.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    if call.data == 'search':
        location_stage(call.message)
        return
    location_id = call.data[6:]
    city = db.get_location(user_id, location_id)
    db.set_user_data(user_id=user_id, col='location', data=location_id)
    bot.edit_message_text(f"{text['looking_hotels']} {city}", call.message.chat.id, call.message.message_id)
    command = db.get_user_data(user_id=user_id, col='command')
    db.set_user_data(user_id=user_id, col='city', data=city)
    Stages.instances[command].go_to_next_stage(call.message)


def checkin_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    min_date = datetime.today()
    max_date = min_date + timedelta(days=60)
    calendar, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                            calendar_id='checkin', locale='ru').build()
    bot.send_message(message.chat.id, text['checkin'], reply_markup=calendar)


@bot.callback_query_handler(func=WMonthTelegramCalendar.func(calendar_id='checkin'))
def from_checkin_stage(call: types.CallbackQuery):
    text = languages[db.get_user_data(user_id=call.from_user.id, col='lang')]
    command = db.get_user_data(user_id=call.from_user.id, col='command')
    min_date = datetime.today()
    max_date = min_date + timedelta(days=60)
    result, key, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                               calendar_id='checkin').process(call.data)
    if not result and key:
        bot.edit_message_text(text['checkin'], call.message.chat.id, call.message.message_id, reply_markup=key)
    elif result:
        bot.edit_message_text(f"{text['accept_checkin']} {result}", call.message.chat.id, call.message.message_id)
        db.set_user_data(user_id=call.from_user.id, col='checkin', data=result.strftime("%Y-%m-%d"))
        Stages.instances[command].go_to_next_stage(call.message)


def checkout_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    min_date = datetime.strptime(db.get_user_data(user_id=message.chat.id, col='checkin'), "%Y-%m-%d")
    max_date = min_date + timedelta(days=60)
    calendar, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                            calendar_id='checkout', locale='ru').build()
    bot.send_message(message.chat.id, text['checkout'], reply_markup=calendar)


@bot.callback_query_handler(func=WMonthTelegramCalendar.func(calendar_id='checkout'))
def from_checkout_stage(call: types.CallbackQuery):
    text = languages[db.get_user_data(user_id=call.from_user.id, col='lang')]
    command = db.get_user_data(user_id=call.from_user.id, col='command')
    min_date = datetime.today()
    max_date = min_date + timedelta(days=60)
    result, key, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                               calendar_id='checkout').process(call.data)
    if not result and key:
        bot.edit_message_text(text['checkout'], call.message.chat.id, call.message.message_id, reply_markup=key)
    elif result:
        bot.edit_message_text(f"{text['accept_checkout']} {result}", call.message.chat.id, call.message.message_id)
        db.set_user_data(user_id=call.from_user.id, col='checkout', data=result.strftime("%Y-%m-%d"))
        Stages.instances[command].go_to_next_stage(call.message)


def min_price_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    bot.send_message(chat_id=message.chat.id, text=text['min_price'])
    bot.register_next_step_handler(message, from_min_price_stage)


def from_min_price_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    try:
        min_price = int(message.text)
        if min_price < 0:
            raise ValueError
    except ValueError:
        message = bot.send_message(message.chat.id, text['error'])
        min_price_stage(message)
    else:
        db.set_user_data(user_id=user_id, col='min_price', data=min_price)
        command = db.get_user_data(user_id=message.chat.id, col='command')
        Stages.instances[command].go_to_next_stage(message)


def max_price_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    bot.send_message(chat_id=message.chat.id, text=text['max_price'])
    bot.register_next_step_handler(message, from_max_price_stage)


def from_max_price_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    min_price = db.get_user_data(user_id=message.chat.id, col='min_price')
    try:
        max_price = int(message.text)
        if max_price < min_price:
            raise ValueError
    except ValueError:
        message = bot.send_message(message.chat.id, f"{text['error']}\n{text['need_greater_price']}")
        max_price_stage(message)
    else:
        db.set_user_data(user_id=user_id, col='max_price', data=max_price)
        command = db.get_user_data(user_id=message.chat.id, col='command')
        Stages.instances[command].go_to_next_stage(message)


def max_distance_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    bot.send_message(chat_id=user_id, text=text['max_distance'])
    bot.register_next_step_handler(message, from_max_distance_stage)


def from_max_distance_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    try:
        max_distance = float(message.text)
        if max_distance < 1:
            raise ValueError
    except ValueError:
        message = bot.send_message(message.chat.id, text=text['error_distance'])
        max_distance_stage(message)
    else:
        db.set_user_data(user_id=user_id, col='max_distance', data=message.text)
        command = db.get_user_data(user_id=message.chat.id, col='command')
        Stages.instances[command].go_to_next_stage(message)


def hotel_number_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    bot.send_message(chat_id=user_id, text=text['hotel_number'])
    bot.register_next_step_handler(message, from_hotel_number_stage)


def from_hotel_number_stage(message):
    user_id = message.from_user.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    try:
        hotels_num = int(message.text)
        if hotels_num < 1 or hotels_num > 50:
            raise ValueError
    except ValueError:
        message = bot.send_message(message.chat.id, text['error_hotels'])
        hotel_number_stage(message)
    else:
        db.set_user_data(user_id=user_id, col='items', data=hotels_num)
        command = db.get_user_data(user_id=message.chat.id, col='command')
        Stages.instances[command].go_to_next_stage(message)


def hotel_photoes_stage(message):
    user_id = message.from_user.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    bot.send_message(chat_id=user_id, text=text['hotel_photoes'])
    bot.register_next_step_handler(message, from_hotel_photoes_stage)


def from_hotel_photoes_stage(message):
    user_id = message.from_user.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    user_id = message.from_user.id
    try:
        photoes_num = int(message.text)
        if photoes_num < 0 or photoes_num > 10:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, text['error_photoes'])
        hotel_photoes_stage(message)
    else:
        db.set_user_data(user_id=user_id, col='photoes', data=photoes_num)
        command = db.get_user_data(user_id=message.chat.id, col='command')
        Stages.instances[command].go_to_next_stage(message)


def final_stage(message):
    user_data = db.get_all_user_data(message.chat.id)
    text = languages[user_data['lang']]
    db.set_user_defaults(user_id=message.chat.id)
    sort_order = Stages.instances[user_data['command']].get_search_method()
    hotels_iter = hotels.query_hotels(data=user_data, sort_order=sort_order)
    #   Вывод информации об отелях
    counter = 1
    result = []
    for hotel in hotels_iter:
        bot.send_message(message.chat.id, f"*{'-' * 23}{counter}{'-' * 23}*\n")
        message_text = f"[{hotel['name']}]({hotel['url']})"
        bot.send_message(message.chat.id, message_text, parse_mode='MarkdownV2', disable_web_page_preview=True)
        bot.send_message(message.chat.id, f"{text['address']}: {hotel['address']}\n"
                                          f"{text['distance']}: {hotel['distance']}\n"
                                          f"{text['price']}: {hotel['price']}\n"
                                          f"{text['total_price']}: {hotel['total_price']}")
        if user_data['photoes'] > 0:
            photoes = hotels.get_hotel_photoes(hotel['id'], user_data['photoes'])
            try:
                bot.send_media_group(message.chat.id, photoes)
            except:
                print(photoes)
                time.sleep(5)
        bot.send_message(message.chat.id, f"*{'-' * 48}*")
        result.append(f'{hotel["name"]}')
        counter += 1
    bot.send_message(message.chat.id, f"{text['finish']}, {user_data['name']}. {text['wait_next']}")
    db.save_user_history(user_data=user_data, result=result)
