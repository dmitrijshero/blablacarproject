import datetime
from mysql.connector import MySQLConnection, Error
from collections import OrderedDict
from config import db_config


user_columns = OrderedDict({'user_id': 'INTEGER PRIMARY KEY UNIQUE NOT NULL',
                            'name': 'VARCHAR(100) NOT NULL',
                            'city': 'VARCHAR(100)',
                            'location': 'VARCHAR(100)',
                            'checkin': 'DATE',
                            'checkout': 'DATE',
                            'items': 'INTEGER',
                            'photoes': 'INTEGER',
                            'command': 'VARCHAR(15)',
                            'stage': 'INTEGER',
                            'min_price': 'INTEGER',
                            'max_price': 'INTEGER',
                            'max_distance': 'VARCHAR(10)',
                            'lang': 'CHAR(2)',
                            })
history_columns = OrderedDict({'id': 'INTEGER PRIMARY KEY UNIQUE NOT NULL',
                               'user_id': 'INTEGER UNIQUE NOT NULL',
                               'start': 'TIMESTAMP NOT NULL',
                               'name': 'VARCHAR(100)',
                               'command': 'VARCHAR(15)',
                               'city': 'VARCHAR(100)',
                               'checkin': 'DATE',
                               'checkout': 'DATE',
                               'items': 'INTEGER',
                               'photoes': 'INTEGER',
                               'min_price': 'INTEGER',
                               'max_price': 'INTEGER',
                               'max_distance': 'VARCHAR(10)',
                               'stop': 'TIMESTAMP',
                               'result': 'VARCHAR(4000)'
                               })
city_search_columns = OrderedDict({'user_id': 'INTEGER NOT NULL',
                                   'location_id': 'INTEGER NOT NULL',
                                   'city': 'VARCHAR(100)',
                                   })


def __create_table(table: str, table_columns: dict, foreing_key=None) -> None:
    create_query = f'CREATE TABLE IF NOT EXISTS {table}('
    query = []
    for column, typeing in table_columns.items():
        query.append(f'{column} {typeing}')
    if foreing_key:
        query.append(f"""FOREIGN KEY ({foreing_key[0]}) REFERENCES {foreing_key[1]} ({foreing_key[2]})
                         ON DELETE CASCADE""")
    query_string = "".join((create_query, ", ".join(query), ")"))
    cursor.execute(query_string)


def insert_user(user_id: int, name: str, language='en'):
    query = 'INSERT INTO users (user_id, name, command, stage, lang) VALUES (?, ?, ?, ?, ?)'
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(query, (user_id, name, 'start', 0, language))


def set_user_defaults(user_id: int):
    name = get_user_data(user_id=user_id, col='name')
    query = f"DELETE FROM users WHERE user_id = {user_id}"
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(query)
        query = 'INSERT INTO users (user_id, name, command, stage, lang) VALUES (?, ?, ?, ?, ?)'
        cur.execute(query, (user_id, name, 'start', 0, 'en'))


def set_user_data(user_id: int, col: str, data):
    with MySQLConnection(**db_config).cursor() as cur:
        if col in user_columns.keys():
            cur.execute(f"""UPDATE users SET {col} = "{data}" WHERE user_id = {user_id}""")
        elif col == 'search':
            for item in data:
                query = 'INSERT INTO search (user_id, location_id, city) VALUES (?, ?, ?)'
                cur.execute(query, (user_id, item['location_id'], item['city']))
        else:
            return False
        return True


def get_user_data(user_id: int, col: str):
    with MySQLConnection(**db_config).cursor() as cur:
        if col in user_columns.keys():
            cur.execute(f'SELECT {col} FROM users WHERE user_id = {user_id}')
            return cur.fetchone()[0]
        elif col.startswith('search'):
            query = f'SELECT city FROM search WHERE user_id = {user_id} AND location_id = {col[6:]}'
            cur.execute(query)
            return cur.fetchone()[0]
        else:
            return None


def get_all_user_data(user_id: int):
    user_data = dict()
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(f'SELECT * FROM users WHERE user_id = {user_id}')
        row = cur.fetchone()
    counter = 0
    for key in user_columns:
        user_data[key] = row[counter]
        counter += 1
    return user_data


def check_user(user_id: int):
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(f'SELECT user_id FROM users WHERE user_id = {user_id}')
        result = cur.fetchone()
    return not (result is None)


def history_start_command(user_id: int) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = 'INSERT INTO history (user_id, start) VALUES (?, ?)'
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(query, (user_id, now))


def save_user_history(user_data: dict, result: list) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with MySQLConnection(**db_config).cursor() as cur:
        cur.execute(f"SELECT id FROM history WHERE user_id = {user_data['user_id']} ORDER BY id DESC LIMIT 1")
        row_id = cur.fetchone()[0]
        query = f"""UPDATE history SET stop = "{now}", name = "{user_data['name']}", command = "{user_data['command']}",
            city = "{user_data['city']}", items = {user_data['items']}, photoes = {user_data['photoes']},
            checkin = "{user_data['checkin']}", checkout = "{user_data['checkout']}", result = \"{", ".join(result)}\"
            WHERE id = {row_id}"""
        cur.execute(query)
        if user_data['command'] == 'bestdeal':
            query = f"""UPDATE history SET min_price = {user_data['min_price']}, max_price = {user_data['max_price']},
                    max_distance = "{user_data['max_distance']}" WHERE id = {row_id}"""
            cur.execute(query)


def get_history_data(user_id: int, check=False) -> list:
    with MySQLConnection(**db_config).cursor() as cur:
        if check:
            cur.execute(f"""SELECT id FROM history WHERE user_id = {user_id} AND command != "history" """)
            return cur.fetchone()[0]
        cur.execute(f"""SELECT * FROM history WHERE user_id = {user_id} AND command != "history" """)
        data = cur.fetchall()
        result = list()
    for entry in data:
        elem = dict()
        for index, key in enumerate(history_columns.keys()):
            elem[key] = entry[index]
        result.append(elem)
    return result


with MySQLConnection(**db_config) as sql_connection:
    cursor = sql_connection.cursor()
    __create_table(table='users', table_columns=user_columns)
    __create_table(table='history', table_columns=history_columns)
    __create_table(table='search', table_columns=city_search_columns, foreing_key=('user_id', 'users', 'user_id'))
