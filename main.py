import os
from dotenv import load_dotenv

from src.api import OpenSkyAPI
from src.DBclass import DBManager


if __name__ == '__main__':
    # Параметры подключения к серверу PostgreSQL (без указания конкретной БД)
    load_dotenv()

    db_params = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }

    # Имя вашей целевой базы данных для курсовой
    target_db = os.getenv("DB_NAME", "sky_tracker")

    # 1. Пересоздаем базу данных и таблицы с нуля
    DBManager.create_database(target_db, db_params)

    # 2. Добавляем имя нашей базы в параметры для дальнейшей работы через DBManager
    db_params["dbname"] = target_db
    db = DBManager(db_params)

    print("Загрузка данных из API и наполнение БД...")
    # Инициализируем класс из скриншота
    api = OpenSkyAPI()

    target_countries = ["Germany", "France", "Poland", "Italy"]

    for country in target_countries:
        print(f"Обработка: {country}")

        # 1. Получаем кортеж координат через класс
        bbox = api.get_country_bbox(country)

        # Переводим в словарь для вашей функции insert_country
        bounds_dict = {
            "lat_min": bbox[0],
            "lat_max": bbox[1],
            "lon_min": bbox[2],
            "lon_max": bbox[3]
        }

        # 2. Записываем страну в БД
        country_id = db.insert_country(country, bounds_dict)

        # 3. Получаем самолеты через класс
        aircrafts = api.get_aeroplanes(country)

        # 4. Записываем самолеты в БД
        for plane in aircrafts:
            if plane[5] is not None and plane[6] is not None:
                db.insert_aeroplane(plane, country_id)

    print("\n=== Проверка методов DBManager ===")

    print("\n1. Количество самолетов по странам:")
    print(db.get_countries_and_aeroplanes_count())

    print("\n2. Средняя скорость самолетов (м/с):")
    avg_speed = db.get_avg_speed()
    print(f"{avg_speed:.2f} м/с")

    print("\n3. Несколько самолетов со скоростью выше средней:")
    print(db.get_aeroplanes_with_higher_speed()[:5])

    print("\n4. Поиск самолетов по ключевому слову в позывном (например, 'A'):")
    print(db.get_aeroplanes_with_keyword("A")[:5])

    db.close()