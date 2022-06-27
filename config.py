import os

import telebot

TOKEN = os.environ.get('TELE_TOKEN')
bot = telebot.TeleBot(token=TOKEN)

location_url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
prop_list_url = 'https://hotels4.p.rapidapi.com/properties/list'
get_photos_url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

rapidapi_headers = {
    'X-RapidAPI-Host': 'hotels4.p.rapidapi.com',
    'X-RapidAPI-Key': os.environ.get('RAPID_KEY')
}
log_file_name = 'log.txt'
