import requests
from telebot import types

from config import (get_photos_url, location_url, prop_list_url,
                    rapidapi_headers)


def escape(text: str) -> str:
    escape_characters = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '\\']
    result = list()
    for sym in text:
        if sym in escape_characters:
            result.append('\\')
        result.append(sym)
    return ''.join(result)
    

def get_location(search_string: str) -> list:
    query = {"query": search_string, "locale": "ru_RU", "currency": "RU"}
    location_response = requests.request("GET", location_url, headers=rapidapi_headers, params=query).json()
    locations = location_response['suggestions'][0]['entities']
    result = []
    for location in locations:
        location_id = location['destinationId']
        city_str = location['caption']
        city_list_str = []
        index1 = 0
        while True:
            index2 = city_str.find('<')
            city_list_str.append(city_str[index1:index2])
            city_str = city_str[index2 + 1:]
            if index2 != -1:
                index1 = city_str.find('>') + 1
            else:
                break
        city = "".join(city_list_str)
        result.append({'location_id':location_id, 'city': city})
    return result


def query_hotels(data: dict, sort_order: str):
    if data['items'] > 25:
        items = '25'
    else:
        items = str(data['items'])
    query = {"destinationId": data['location'], "pageSize": items, "checkIn": data['checkin'],
             "checkOut": data['checkout'], "adults1": "1", "priceMin": data['min_price'],
             "priceMax": data['max_price'], "sortOrder": sort_order, "locale": "en_US", "currency": "USD"}
    hotels_response = requests.request("GET", prop_list_url, headers=rapidapi_headers, params=query).json()
    result = hotels_response["data"]["body"]["searchResults"]["results"]
    if data['items'] > 25:
        query = {"destinationId": data['location'], "pageNumber": "2", "pageSize": str(data['items'] - 25),
                 "checkIn": data['checkin'], "checkOut": data['checkout'], "adults1": "1",
                 "priceMin": data['min_price'], "priceMax": data['max_price'], "sortOrder": sort_order,
                 "locale": "en_US", "currency": "USD"}
        hotels_response = requests.request("GET", prop_list_url, headers=rapidapi_headers, params=query).json()
        result.extend(hotels_response["data"]["body"]["searchResults"]["results"])
    for item in result:
        hotel = dict()
        hotel['id'] = item['id']
        hotel['url'] = f"https://hotels.com/ho{item['id']}"
        hotel['name'] = escape(item['name'])
        hotel['address'] = ', '.join((item['address']['locality'], item['address']['streetAddress'],
                                     item['address']['extendedAddress']), )
        hotel['distance'] = item['landmarks'][0]['distance']
        try:
            hotel['price'] = item['ratePlan']['price']['current']
        except KeyError:
            hotel['price'] = 'Value not found'
        try:
            hotel['total_price'] = item['ratePlan']['price']['fullyBundledPricePerStay'].split()[1]
        except KeyError:
            hotel['total_price'] = 'Value not found'
        yield hotel
        if data['max_distance']:
            if float(hotel['distance'].split(' ')[0]) > data['max_distance']:
                break


def get_hotel_photoes(hotel_id: int, items: int):
    query = {"id": str(hotel_id)}
    hotel_images = requests.request("GET", get_photos_url, headers=rapidapi_headers, params=query).json()['hotelImages']
    result = []
    count = 0
    for image in hotel_images:
        size = max(image['sizes'], key=lambda x: x.get('type'))['suffix']
        base_url = f"{image['baseUrl'][:-10]}{size}{image['baseUrl'][-4:]}"
        result.append(types.InputMediaPhoto(base_url))
        count += 1
        if count >= items:
            break
    return result
