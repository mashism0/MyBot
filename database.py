import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import os
#инициализация подключения
class Database:
    def __init__(self):
        load_dotenv()
        self.conn = psycopg2.connect( #соединение с бд
            dbname=os.getenv("dbname"), user=os.getenv("user"),
            password=os.getenv("password"), host=os.getenv("host")
        )
        self.cursor = self.conn.cursor()  #создание курсора
        #курсор - объект для выполнения SQL - запросов и получения результатов.

    def create_tables_users(self):
        # Создание таблицы пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL NOT NULL PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE, 
                name VARCHAR(100) NOT NULL,
                surname VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                reg_date TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """)

        # Проверяем существование столбца track_id перед добавлением
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' and column_name='track_id'
        """)
        if not self.cursor.fetchone():
            self.cursor.execute("""
                ALTER TABLE users
                ADD COLUMN track_id BIGINT
            """)

        self.conn.commit()


    def create_table_track(self):
        # Создание таблицы трасс
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS track (
                id BIGSERIAL NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                category_1 INT NOT NULL,
                category_2 VARCHAR(2) NOT NULL
            )
        """)
        self.conn.commit()


    def get_user(self, telegram_id: int):
        #Получение данных пользователя по ID
        self.cursor.execute(
            "SELECT * FROM users WHERE telegram_id = %s",
            (telegram_id,)
        )
        return self.cursor.fetchone()

    def user_exists(self, telegram_id):
        #Проверяем существование пользователя
        self.cursor.execute(
            "SELECT 1 FROM users WHERE telegram_id = %s",
            (telegram_id,)
        )
        return bool(self.cursor.fetchone())


    def user_update(self, telegram_id: int, name: str, surname: str, city: str, phone: str):
        try:
            # Проверяем существование пользователя
            self.cursor.execute(
                "SELECT 1 FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )

            if self.cursor.fetchone():
                # Обновляем существующую запись
                self.cursor.execute(
                    """UPDATE users 
                    SET name = %s,
                        surname = %s, 
                        city = %s, 
                        phone = %s,
                    WHERE telegram_id = %s""",
                    (name, surname, city, phone, telegram_id, )
                )
            else:
                print(f"Данные для вставки: {telegram_id}, {name}, {surname}, {city}, {phone}")
                self.cursor.execute(
                    """INSERT INTO users 
                    (telegram_id, name, surname, city, phone, reg_date) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (telegram_id, name, surname, city, phone, datetime.now())
                )
                print(f"Затронуто строк: {self.cursor.rowcount}")  # Должно быть 1
                self.conn.commit()
        except Exception as e:
            print(f"Ошибка при вставке: {type(e).__name__}: {e}")
            self.conn.rollback()
            raise  # Чтобы увидеть стектрейс


    def save_track(self, user_id, date, category_1, category_2):
        try:
            self.cursor.execute(
                """INSERT INTO track 
                (user_id, date, category_1, category_2) 
                VALUES (%s, %s, %s, %s)""",
                (user_id, date, category_1, category_2)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка сохранения трассы: {e}")
            self.conn.rollback()
            return False

    def get_username(self, user_id):
        """Получает имя пользователя из базы данных по его ID"""
        self.cursor.execute("SELECT name FROM users WHERE telegram_id = %s", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None


class Analysis:
    def __init__(self):
        load_dotenv()
        self.conn = psycopg2.connect( #соединение с бд
            dbname=os.getenv("dbname"), user=os.getenv("user"),
            password=os.getenv("password"), host=os.getenv("host")
        )
        self.cursor = self.conn.cursor()  #создание курсора
    def track(self, telegram_id):
        try:
            # Проверяем существование трасс
            self.cursor.execute(
                "SELECT 1 FROM track WHERE user_id = %s",
                (telegram_id,)
            )
            if not self.cursor.fetchone():
                return None
            self.cursor.execute( #соединяем 2 столбца 7 + 'A' = '7A'
                #Подсчитываем количество каждой категории
                #Из количества каждой категории узнаём самую популярную
                """WITH days_30_track AS (
                SELECT category_1::text || category_2 AS category
                FROM track
                WHERE user_id = %s
                AND date BETWEEN CURRENT_DATE - INTERVAL '30 days' AND CURRENT_DATE
            ),
            
            counter_30 AS ( 
                SELECT category, COUNT(*) AS counter_30
                FROM days_30_track
                GROUP BY category
            ),
            
            popular_30 AS (
                SELECT category AS popular30
                FROM counter_30
                ORDER BY counter_30 DESC
                LIMIT 1
            ),
            
            max_30 AS (
                SELECT MAX(category) AS max30
                FROM days_30_track
            ),
            
            days_90_track AS (
                SELECT category_1::text || category_2 AS category
                FROM track
                WHERE user_id = %s
                AND date BETWEEN CURRENT_DATE - INTERVAL '90 days' AND CURRENT_DATE
            ),
        
            counter_90 AS (
                SELECT category, COUNT(*) AS counter_90
                FROM days_90_track
                GROUP BY category
            ),
        
            popular_90 AS (
                SELECT category AS popular90
                FROM counter_90
                ORDER BY counter_90 DESC
                LIMIT 1
            ),
            
            max_90 AS (
                SELECT MAX(category) AS max90
                FROM days_90_track
            )
            
            SELECT popular_30.popular30, max_30.max30,
            popular_90.popular90, max_90.max90
            FROM popular_30, max_30,
            popular_90, max_90;""", (telegram_id, telegram_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Ошибка анализа лазания: {e}")
            self.conn.rollback()

