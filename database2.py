from datetime import datetime,timedelta
import pymysql
from mysql_dbconfig import read_db_config


class DataBase():

    def __check_table(self, cursor, table: str):
        query = f"""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                    WHERE table_schema = '{self.config['database']}' AND TABLE_NAME = '{table}';"""
        cursor.execute(query)
        result = cursor.fetchone()
        if result is None:
            return False
        return True

    def __init__(self):
        self.config = read_db_config()
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            if not self.__check_table(cursor, 'users'):
                query = f"""CREATE TABLE users(
                    user_id INT UNIQUE NOT NULL, 
                    name VARCHAR(200) NOT NULL, 
                    city VARCHAR(200), 
                    location VARCHAR(200), 
                    checkin VARCHAR(100), 
                    checkout VARCHAR(100), 
                    items INT, 
                    photoes INT, 
                    command VARCHAR(30), 
                    stage INT, 
                    min_price INT, 
                    max_price INT, 
                    max_distance VARCHAR(10), 
                    lang CHAR(4),
                    PRIMARY KEY (user_id));"""
                cursor.execute(query)
            if not self.__check_table(cursor, 'history'):
                query = f"""CREATE TABLE history(
                            id INT NOT NULL AUTO_INCREMENT,
                            user_id INT NOT NULL, 
                            start TIMESTAMP NOT NULL,
                            name VARCHAR(200),
                            command VARCHAR(30),
                            city VARCHAR(200),
                            checkin DATE,
                            checkout DATE,
                            items INT,
                            photoes INT,
                            min_price INT,
                            max_price INT,
                            max_distance VARCHAR(10),
                            stop TIMESTAMP,
                            result VARCHAR(8000),
                            PRIMARY KEY (id));"""
                cursor.execute(query)
            if not self.__check_table(cursor, 'search'):
                query = f"""CREATE TABLE search(
                            user_id INT NOT NULL, 
                            location_id INT NOT NULL,
                            city VARCHAR(200));"""
                cursor.execute(query)
            connection.commit()
            query = "SHOW columns FROM users"
            cursor.execute(query)
            self.user_columns = [column[0] for column in cursor.fetchall()]
            query = "SHOW columns FROM history"
            cursor.execute(query)
            self.history_columns = [column[0] for column in cursor.fetchall()]
            query = "SHOW columns FROM search"
            cursor.execute(query)
            self.search_columns = [column[0] for column in cursor.fetchall()]
        connection.close()

    def insert_user(self, user_id: int, name: str, language='en'):
        query = 'INSERT INTO users (user_id, name, command, stage, lang) VALUES (%s, %s, %s, %s, %s)'
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(query, (user_id, name, 'start', 0, language))
        connection.commit()
        connection.close()

    def set_user_defaults(self, user_id: int):
        name = self.get_user_data(user_id=user_id, col='name')
        query = f"DELETE FROM users WHERE user_id = {user_id}"
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(query)
            query = 'INSERT INTO users (user_id, name, command, stage, lang) VALUES (%s, %s, %s, %s, %s)'
            cursor.execute(query, (user_id, name, 'start', 0, 'en'))
        connection.commit()
        connection.close()

    def set_user_data(self, user_id: int, col: str, data):
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            if col in self.user_columns:
                cursor.execute(f"""UPDATE users SET {col} = "{data}" WHERE user_id = {user_id}""")
            elif col == 'search':
                for item in data:
                    query = 'INSERT INTO search (user_id, location_id, city) VALUES (%s, %s, %s)'
                    cursor.execute(query, (user_id, item['location_id'], item['city']))
            else:
                return False
        connection.commit()
        connection.close()
        return True

    def get_user_data(self, user_id: int, col: str):
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            if col in self.user_columns:
                cursor.execute(f'SELECT {col} FROM users WHERE user_id = {user_id}')
                result = cursor.fetchone()[0]
            elif col.startswith('search'):
                query = f'SELECT city FROM search WHERE user_id = {user_id} AND location_id = {col[6:]}'
                cursor.execute(query)
                result = cursor.fetchone()[0]
            else:
                result = None
        connection.close()
        return result

    def get_all_user_data(self, user_id: int):
        user_data = dict()
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM users WHERE user_id = {user_id}')
            row = cursor.fetchone()
        for index, key in enumerate(self.user_columns):
            user_data[key] = row[index]
        connection.close()
        return user_data

    def check_user(self, user_id: int):
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT user_id FROM users WHERE user_id = {user_id}')
            result = cursor.fetchone()
        connection.close()
        return not (result is None)

    def history_start_command(self, user_id: int) -> None:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = 'INSERT INTO history (user_id, start) VALUES (%s, %s)'
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(query, (user_id, now))
        connection.commit()
        connection.close()

    def save_user_history(self, user_data: dict, result: list) -> None:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id FROM history WHERE user_id = {user_data['user_id']} ORDER BY id DESC LIMIT 1")
            row_id = cursor.fetchone()[0]
            query = f"""UPDATE history SET stop = "{now}", name = "{user_data['name']}", command = "{user_data['command']}",
                city = "{user_data['city']}", items = {user_data['items']}, photoes = {user_data['photoes']},
                checkin = "{user_data['checkin']}", checkout = "{user_data['checkout']}", result = \"{", ".join(result)}\"
                WHERE id = {row_id}"""
            cursor.execute(query)
            if user_data['command'] == 'bestdeal':
                query = f"""UPDATE history SET min_price = {user_data['min_price']}, max_price = {user_data['max_price']},
                        max_distance = "{user_data['max_distance']}" WHERE id = {row_id}"""
                cursor.execute(query)
        connection.commit()
        connection.close()

    def get_history_data(self, user_id: int, start=None, stop=None, check=False):
        try:
            connection = pymysql.connect(**self.config)
        except Exception as e:
            print(e)
            return
        if check:
            with connection.cursor() as cursor:
                cursor.execute(f"""SELECT id FROM history WHERE user_id = {user_id} AND command != "history" """)
            connection.close()
            return cursor.fetchone()[0]
        finish = datetime.strftime(datetime.strptime(stop,'%Y-%m-%d') + timedelta(days=1), "%Y-%m-%d")
        with connection.cursor() as cursor:
            query = f"""SELECT * FROM history WHERE user_id = {user_id} AND command != "history"
                    AND (start BETWEEN  STR_TO_DATE('{start}', '%Y-%m-%d') 
                    AND STR_TO_DATE('{finish}', '%Y-%m-%d'));"""
            cursor.execute(query)
        data = cursor.fetchall()
        result = list()
        for entry in data:
            elem = dict()
            for index, key in enumerate(self.history_columns):
                elem[key] = entry[index]
            result.append(elem)
        connection.close()
        return result


database = DataBase()
