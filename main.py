import os
from dotenv import load_dotenv

import time
from src.utils import get_country_bounds, get_aircrafts_in_bbox
from src.DBclass import DBManager, create_database


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
    DB_NAME = os.getenv("DB_NAME", "sky_tracker")

    # 1. Пересоздаем базу данных и таблицы с нуля
    create_database(DB_NAME, db_params)

    # 2. Добавляем имя нашей базы в параметры для дальнейшей работы через DBManager
    db_params["dbname"] = DB_NAME
    db = DBManager(db_params)
    db.clear_tables()

    print("Загрузка данных из API и наполнение БД...")
    target_countries = ["Germany", "France", "Poland", "Italy"]

    print("Загрузка данных из API и наполнение БД...")

    for country in target_countries:
        print(f"Обработка: {country}")
        bounds = get_country_bounds(country)

        if bounds:
            # Записываем страну в БД и получаем её ID
            country_id = db.insert_country(country, bounds)

            # Тянем самолеты из OpenSky
            aircrafts = get_aircrafts_in_bbox(bounds)
            print(f"  -> Найдено самолетов в воздухе: {len(aircrafts)}")

            # Наполняем таблицу самолетов
            for plane in aircrafts:
                # Проверяем, что в данных есть координаты долготы и широты
                if plane[5] is not None and plane[6] is not None:
                    db.insert_aeroplane(plane, country_id)

        # Небольшая пауза между странами, чтобы OpenSky не заблокировал за частые запросы
        time.sleep(2)

    # for country in target_countries:
    #     print(f"Обработка: {country}")
    #     bounds = get_country_bounds(country)
    #
    #     # ОТЛАДКА: проверяем, получили ли мы границы страны
    #     print(f"  -> Результат поиска границ: {bounds}")
    #
    #     if bounds:
    #         country_id = db.insert_country(country, bounds)
    #         aircrafts = get_aircrafts_in_bbox(bounds)
    #
    #         # ОТЛАДКА: проверяем, сколько самолетов выдал OpenSky
    #         print(f"  -> Найдено самолетов в воздухе: {len(aircrafts)}")
    #
    #         for plane in aircrafts:
    #             # В OpenSky: plane[5] - долгота, plane[6] - широта
    #             if plane[5] is not None and plane[6] is not None:
    #                 db.insert_aeroplane(plane, country_id)
    #     else:
    #         print(f"  [!] Ошибка: Не удалось получить bounds для {country}")
    #     # Пауза, чтобы не спамить API OpenStreetMap (Nominatim просит не более 1 запроса в секунду)
    #     time.sleep(2)

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