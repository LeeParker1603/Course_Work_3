import psycopg2

class DBManager:

    def __init__(self, db_params: dict):
        # Принимает параметры, где уже обязательно должен быть указан "dbname"
        self.conn = psycopg2.connect(**db_params)
        self.conn.autocommit = True

    @staticmethod
    def create_database(database_name: str, params: dict) -> None:
        """Создает базу данных и таблицы с нуля.

        Вызывается без создания экземпляра класса.
        """
        # Шаг 1: Подключаемся к системной базе postgres, чтобы управлять другими БД
        conn = psycopg2.connect(dbname="postgres", **params)
        conn.autocommit = True
        cur = conn.cursor()

        # Принудительно отключаем другие сессии от целевой базы, чтобы избежать ошибок блокировки
        cur.execute(
            f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database_name}'
              AND pid <> pg_backend_pid();
        """
        )

        # Пересоздаем саму базу данных
        cur.execute(f"DROP DATABASE IF EXISTS {database_name};")
        cur.execute(f"CREATE DATABASE {database_name};")

        cur.close()
        conn.close()

        # Шаг 2: Подключаемся к уже созданной базе и создаем в ней таблицы
        conn = psycopg2.connect(dbname=database_name, **params)
        conn.autocommit = True
        cur = conn.cursor()

        # Таблица стран
        cur.execute(
            """
            CREATE TABLE countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                lat_min NUMERIC NOT NULL,
                lat_max NUMERIC NOT NULL,
                lon_min NUMERIC NOT NULL,
                lon_max NUMERIC NOT NULL
            );
        """
        )

        # Таблица самолетов
        cur.execute(
            """
            CREATE TABLE aeroplanes (
                icao24 VARCHAR(10) PRIMARY KEY,
                callsign VARCHAR(20),
                origin_country VARCHAR(100),
                longitude NUMERIC,
                latitude NUMERIC,
                velocity NUMERIC,
                country_id INT REFERENCES countries(id) ON DELETE CASCADE
            );
        """
        )

        cur.close()
        conn.close()
        print(f"База данных {database_name} и таблицы успешно созданы!")

    def insert_country(self, name: str, bounds: dict) -> int:
        """Добавляет страну в таблицу и возвращает её ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO countries (name, lat_min, lat_max, lon_min, lon_max)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
                """,
                (
                    name,
                    bounds["lat_min"],
                    bounds["lat_max"],
                    bounds["lon_min"],
                    bounds["lon_max"],
                ),
            )
            return cur.fetchone()[0]

    def insert_aeroplane(self, state: list, country_id: int) -> None:
        """Сохраняет данные о самолете из ответа OpenSky."""
        with self.conn.cursor() as cur:
            icao24 = state[0]
            callsign = state[1].strip() if state[1] else None
            origin_country = state[2]
            longitude = state[5]
            latitude = state[6]
            velocity = state[9]

            cur.execute(
                """
                INSERT INTO aeroplanes (icao24, callsign, origin_country, longitude, latitude, velocity, country_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (icao24) DO UPDATE SET
                    callsign = EXCLUDED.callsign,
                    longitude = EXCLUDED.longitude,
                    latitude = EXCLUDED.latitude,
                    velocity = EXCLUDED.velocity;
                """,
                (
                    icao24,
                    callsign,
                    origin_country,
                    longitude,
                    latitude,
                    velocity,
                    country_id,
                ),
            )

    def get_countries_and_aeroplanes_count(self):
        """Обязательный метод: считает количество самолетов по странам."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, COUNT(a.icao24) 
                FROM countries c
                LEFT JOIN aeroplanes a ON c.id = a.country_id
                GROUP BY c.name;
            """
            )
            return cur.fetchall()

    def get_all_aeroplanes(self):
        """Обязательный метод: возвращает список всех воздушных судов."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT icao24, callsign, origin_country, velocity FROM aeroplanes;"
            )
            return cur.fetchall()

    def get_avg_speed(self):
        """Обязательный метод: считает среднюю скорость по всем самолетам."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT AVG(velocity) FROM aeroplanes WHERE velocity IS NOT NULL;"
            )
            res = cur.fetchone()
            return float(res[0]) if res[0] is not None else 0.0

    def get_aeroplanes_with_higher_speed(self):
        """Обязательный метод: возвращает самолеты со скоростью выше средней."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT icao24, callsign, velocity 
                FROM aeroplanes 
                WHERE velocity > (SELECT AVG(velocity) FROM aeroplanes WHERE velocity IS NOT NULL);
            """
            )
            return cur.fetchall()

    def get_aeroplanes_with_keyword(self, keyword: str):
        """Обязательный метод: ищет самолеты по ключевому слову в позывном."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT icao24, callsign FROM aeroplanes WHERE callsign ILIKE %s;",
                (f"%{keyword}%",),
            )
            return cur.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()