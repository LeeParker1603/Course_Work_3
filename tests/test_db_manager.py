import os
import pytest
from dotenv import load_dotenv
from src.DBclass import DBManager

load_dotenv()

TEST_DB_NAME = "sky_tracker_test"


@pytest.fixture(scope="module")
def db_params():
    """Фикстура параметров подключения к серверу PostgreSQL."""
    return {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }


@pytest.fixture(scope="module")
def db_manager(db_params):
    """Фикстура для автоматического создания и удаления тестовой БД."""
    clean_params = db_params.copy()
    clean_params.pop("dbname", None)

    # 1. Создаем тест-базу через ваш статический метод
    DBManager.create_database(TEST_DB_NAME, clean_params)

    clean_params["dbname"] = TEST_DB_NAME
    manager = DBManager(clean_params)

    # 2. Записываем тестовую страну
    bounds = {"lat_min": 40.0, "lat_max": 50.0, "lon_min": 10.0,
              "lon_max": 20.0}
    country_id = manager.insert_country("TestCountry", bounds)

    # 3. Записываем 3 тестовых самолета
    # Структура списка строго соответствует индексам OpenSky: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    # Индексы: 0=icao, 1=callsign, 2=country, 5=lon, 6=lat, 9=velocity
    manager.insert_aeroplane(
        ["plane1", "ACA123", "Canada", None, None, 12.0, 42.0, None, False,
         200.0], country_id)
    manager.insert_aeroplane(
        ["plane2", "DLH456", "Germany", None, None, 14.0, 44.0, None, False,
         300.0], country_id)
    manager.insert_aeroplane(
        ["plane3", "ACA789", "Canada", None, None, 16.0, 46.0, None, False,
         100.0], country_id)

    yield manager

    # --- БЛОК ОЧИСТКИ (ТЕАРДАУН) ---
    # 1. Сначала принудительно закрываем соединение менеджера
    try:
        manager.close()
    except Exception:
        pass

    # 2. Подключаемся к postgres и принудительно выгоняем всех зависших пользователей из тест-базы
    import psycopg2
    try:
        conn = psycopg2.connect(dbname="postgres", **clean_params)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Отключаем всех, кто держит базу sky_tracker_test открытой
            cur.execute(f"""
                   SELECT pg_terminate_backend(pg_stat_activity.pid)
                   FROM pg_stat_activity
                   WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
                     AND pid <> pg_backend_pid();
               """)
            # Теперь спокойно удаляем её
            cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
        conn.close()
    except Exception as e:
        print(f"Предупреждение при удалении тест-базы: {e}")


# --- ТЕСТЫ БАЗЫ ДАННЫХ ---

def test_get_countries_and_aeroplanes_count(db_manager):
    """Тест подсчета количества самолетов в странах."""
    result = db_manager.get_countries_and_aeroplanes_count()
    assert len(result) == 1
    assert result[0][0] == "TestCountry"
    assert result[0][1] == 3


def test_get_all_aeroplanes(db_manager):
    """Тест получения списка всех воздушных судов."""
    result = db_manager.get_all_aeroplanes()
    assert len(result) == 3
    # Собираем все icao24 из кортежей ответа БД
    icaos = [row[0] for row in result]
    assert "plane1" in icaos
    assert "plane2" in icaos


def test_get_avg_speed(db_manager):
    """Тест вычисления средней скорости: (200 + 300 + 100) / 3 = 200."""
    assert db_manager.get_avg_speed() == 200.0


def test_get_aeroplanes_with_higher_speed(db_manager):
    """Тест получения самолетов со скоростью выше средней (> 200)."""
    result = db_manager.get_aeroplanes_with_higher_speed()
    assert len(result) == 1
    assert result[0][0] == "plane2"  # У него скорость 300


def test_get_aeroplanes_with_keyword(db_manager):
    """Тест поиска самолетов по ключевому слову в позывном."""
    result = db_manager.get_aeroplanes_with_keyword("ACA")
    assert len(result) == 2  # Должны найтись ACA123 и ACA789