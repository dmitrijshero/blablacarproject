from datetime import datetime

from telebot import types
from telegram_bot_calendar import WMonthTelegramCalendar

from languages import languages
from botrequests.dialogs import Stages
from config import bot
from database2 import database as db


def start_date_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    if db.get_history_data(user_id=message.chat.id, check=True) is None:
        bot.send_message(message.chat.id, text['history_empty'])
        db.set_user_defaults(user_id=message.chat.id)
        return
    max_date = datetime.today()
    calendar, step = WMonthTelegramCalendar(max_date=max_date.date(), calendar_id='start', locale='ru').build()
    bot.send_message(message.chat.id, text['history_date_from'], reply_markup=calendar)


@bot.callback_query_handler(func=WMonthTelegramCalendar.func(calendar_id='start'))
def from_start_date_stage(call: types.CallbackQuery):
    text = languages[db.get_user_data(user_id=call.message.chat.id, col='lang')]
    max_date = datetime.today()
    result, key, step = WMonthTelegramCalendar(max_date=max_date.date(), calendar_id='start').process(call.data)
    if not result and key:
        bot.edit_message_text(text['history_date_from'], call.message.chat.id,
                              call.message.message_id, reply_markup=key)
    elif result:
        bot.edit_message_text(f"{text['from']} {result}", call.message.chat.id, call.message.message_id)
        db.set_user_data(user_id=call.from_user.id, col='checkin', data=result.strftime("%Y-%m-%d"))
        stages.go_to_next_stage(call.message)


def finish_date_stage(message):
    text = languages[db.get_user_data(user_id=message.chat.id, col='lang')]
    min_date = datetime.strptime(db.get_user_data(user_id=message.chat.id, col='checkin'), "%Y-%m-%d")
    max_date = datetime.today()
    calendar, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                            calendar_id='finish', locale='ru').build()
    bot.send_message(message.chat.id, text['history_date_to'], reply_markup=calendar)


@bot.callback_query_handler(func=WMonthTelegramCalendar.func(calendar_id='finish'))
def from_finish_date_stage(call: types.CallbackQuery):
    text = languages[db.get_user_data(user_id=call.message.chat.id, col='lang')]
    min_date = datetime.strptime(db.get_user_data(user_id=call.from_user.id, col='checkin'), "%Y-%m-%d")
    max_date = datetime.today()
    result, key, step = WMonthTelegramCalendar(min_date=min_date.date(), max_date=max_date.date(),
                                               calendar_id='finish').process(call.data)
    if not result and key:
        bot.edit_message_text(text['history_date_to'], call.message.chat.id,
                              call.message.message_id, reply_markup=key)
    elif result:
        bot.edit_message_text(f"{text['to']} {result}", call.message.chat.id, call.message.message_id)
        db.set_user_data(user_id=call.from_user.id, col='checkout', data=result.strftime("%Y-%m-%d"))
        stages.go_to_next_stage(call.message)


def final_stage(message):
    user_id = message.chat.id
    text = languages[db.get_user_data(user_id=user_id, col='lang')]
    start_date = db.get_user_data(user_id=user_id, col='checkin')
    finish_date = db.get_user_data(user_id=user_id, col='checkout')
    history = db.get_history_data(user_id, start=start_date, stop=finish_date)
    if len(history) == 0:
        bot.send_message(message.chat.id, text['history_empty'])
    else:
        counter = 1
        message_elements = [f"{text['history']}:\n", ]
        for entry in history:
            string_list = [f"\n*{'-' * 23}{counter}{'-' * 23}*\n",]
            string_list.append(text['history_str_1'].format(
                entry['start'], entry['command'], entry['items'], entry['city'], entry['photoes']))
            if entry['command'] == "bestdeal":
                string_list.append(text['history_str_2'].format(
                    entry['min_price'], entry['max_price'], entry['max_distance']))
            string_list.append(text['history_str_3'].format(entry['stop'], entry['result']))
            entry_text = "".join(string_list)  # элемент истории
            message_length = 0
            for item in message_elements:
                message_length += len(item)
            message_length += len(entry_text)
            if message_length < 4000:
                message_elements.append(entry_text)
            else:
                bot.send_message(message.chat.id, "".join(message_elements))
                message_elements = [entry_text, ]
            counter += 1
        message_elements.append(f"*{'-' * 50}*\n")
        bot.send_message(message.chat.id, "".join(message_elements))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bot.send_message(message.chat.id, f"Отчет составлен {now}")
    db.set_user_defaults(user_id=message.chat.id)


script = [start_date_stage, finish_date_stage, final_stage]

stages = Stages('history', script)
