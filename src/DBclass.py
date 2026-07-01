import psycopg2

def create_database(database_name: str, params: dict) -> None:
    """Создание базы данных и таблиц для сохранения данных о самолетах."""
    # Подключаемся к дефолтной базе postgres, чтобы иметь права на создание новой БД
    conn = psycopg2.connect(dbname='postgres', **params)
    conn.autocommit = True  # Это строго обязательно ДО создания курсора
    cur = conn.cursor()

    cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database_name}'
              AND pid <> pg_backend_pid();
        """)

    # Удаляем старую БД, если она существует, и создаем новую
    cur.execute(f"DROP DATABASE IF EXISTS {database_name};")
    cur.execute(f"CREATE DATABASE {database_name};")

    cur.close()
    conn.close()

    # Подключаемся уже к НАШЕЙ НОВОЙ базе данных, чтобы создать в ней таблицы
    conn = psycopg2.connect(dbname=database_name, **params)
    conn.autocommit = True
    cur = conn.cursor()

    # Создаем таблицу стран
    cur.execute("""
        CREATE TABLE countries (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            lat_min NUMERIC NOT NULL,
            lat_max NUMERIC NOT NULL,
            lon_min NUMERIC NOT NULL,
            lon_max NUMERIC NOT NULL
        );
    """)

    # Создаем таблицу самолетов
    cur.execute("""
        CREATE TABLE aeroplanes (
            icao24 VARCHAR(10) PRIMARY KEY,
            callsign VARCHAR(20),
            origin_country VARCHAR(100),
            longitude NUMERIC,
            latitude NUMERIC,
            velocity NUMERIC,
            country_id INT REFERENCES countries(id) ON DELETE CASCADE
        );
    """)

    cur.close()
    conn.close()
    print(f"База данных {database_name} и таблицы успешно созданы!")


class DBManager:
    def __init__(self, db_params):
        self.conn = psycopg2.connect(**db_params)
        self.conn.autocommit = True

    def clear_tables(self):
        """Очистка таблиц перед новым запуском."""
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE aeroplanes, countries RESTART IDENTITY CASCADE;")

    def insert_country(self, name, bounds):
        """Добавляет страну и возвращает её ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO countries (name, lat_min, lat_max, lon_min, lon_max)
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """,
                (name, bounds["lat_min"], bounds["lat_max"], bounds["lon_min"], bounds["lon_max"])
            )
            return cur.fetchone()[0]

    def insert_aeroplane(self, state, country_id):
        """Сохраняет данные о самолете."""
        with self.conn.cursor() as cur:
            # Исключаем пустые или некорректные позывные
            callsign = state[1].strip() if state[1] else None
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
                (state[0], callsign, state[2], state[5], state[6], state[9], country_id)
            )

    # --- Обязательные методы по заданию ---

    def get_countries_and_aeroplanes_count(self):
        """Список всех стран и количество самолетов в их воздушном пространстве."""
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
        """Список всех воздушных судов."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT icao24, callsign, origin_country, velocity FROM aeroplanes;")
            return cur.fetchall()

    def get_avg_speed(self):
        """Средняя скорость по самолетам."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT AVG(velocity) FROM aeroplanes WHERE velocity IS NOT NULL;")
            res = cur.fetchone()[0]
            return float(res) if res else 0.0

    def get_aeroplanes_with_higher_speed(self):
        """Список всех самолетов, у которых скорость выше средней."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT icao24, callsign, velocity 
                FROM aeroplanes 
                WHERE velocity > (SELECT AVG(velocity) FROM aeroplanes WHERE velocity IS NOT NULL);
                """
            )
            return cur.fetchall()

    def get_aeroplanes_with_keyword(self, keyword):
        """Список самолетов, в позывном которых содержатся переданные символы."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT icao24, callsign FROM aeroplanes WHERE callsign ILIKE %s;",
                (f"%{keyword}%",)
            )
            return cur.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()