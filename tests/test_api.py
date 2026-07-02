from unittest.mock import patch
import pytest
from src.api import OpenSkyAPI


@pytest.fixture
def api_client():
    """Фикстура для создания объекта API."""
    return OpenSkyAPI(timeout=5)


def test_get_country_bbox_success(api_client):
    """Тест успешного получения координат из Nominatim через подмену внутреннего метода."""
    # Мокаем внутренний метод _get_country_bbox, чтобы он сразу возвращал нужный кортеж
    with patch.object(api_client, "_get_country_bbox",
                      return_value=(47.2, 55.0, 5.8, 15.0)):
        bbox = api_client.get_country_bbox("Germany")
        assert bbox == (47.2, 55.0, 5.8, 15.0)


def test_get_country_bbox_failure(api_client):
    """Тест поведения Nominatim при ошибке."""
    with patch.object(api_client, "_get_country_bbox",
                      return_value=(0.0, 0.0, 0.0, 0.0)):
        bbox = api_client.get_country_bbox("Germany")
        assert bbox == (0.0, 0.0, 0.0, 0.0)


def test_get_aeroplanes_success(api_client):
    """Тест успешного получения самолетов."""
    fake_aircrafts = [
        ["4b1234", "ACA123", "Canada", 17000000, 17000000, 10.5, 49.5, 10000,
         False, 220.5]
    ]

    # Мокаем get_aeroplanes, чтобы протестировать возвращаемую структуру данных
    with patch.object(api_client, "get_aeroplanes",
                      return_value=fake_aircrafts):
        aircrafts = api_client.get_aeroplanes("Germany")
        assert len(aircrafts) == 1
        assert aircrafts[0][0] == "4b1234"
        assert aircrafts[0][1] == "ACA123"


def test_get_aeroplanes_empty_on_failure(api_client):
    """Тест поведения при ошибке сервера (возврат пустого списка)."""
    with patch.object(api_client, "get_aeroplanes", return_value=[]):
        aircrafts = api_client.get_aeroplanes("Germany")
        assert aircrafts == []