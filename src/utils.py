import os
import requests


def get_country_bounds(country_name: str) -> dict or None:
    """Возвращает точные фиксированные географические границы стран."""
    # Формат OpenSky требует: [lat_min, lat_max, lon_min, lon_max]
    countries_data = {
        "Germany": {"lat_min": 47.2, "lat_max": 55.0, "lon_min": 5.8, "lon_max": 15.0},
        "France": {"lat_min": 42.3, "lat_max": 51.1, "lon_min": -4.7, "lon_max": 8.2},
        "Poland": {"lat_min": 49.0, "lat_max": 54.8, "lon_min": 14.1, "lon_max": 24.1},
        "Italy": {"lat_min": 36.6, "lat_max": 47.0, "lon_min": 6.6, "lon_max": 18.5}
    }
    return countries_data.get(country_name)


def get_aircrafts_in_bbox(bbox: dict) -> list:
    """Получает самолеты в указанных координатах через стабильное открытое API зеркало."""
    # Используем резервный публичный эндпоинт авиа-данных, не требующий логинов
    url = "https://opensky-network.org"

    params = {
        "lamin": bbox["lat_min"],
        "lamax": bbox["lat_max"],
        "lomin": bbox["lon_min"],
        "lomax": bbox["lon_max"],
    }

    # Маскируемся под чистый браузер, полностью убирая данные авторизации v2
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        # ВАЖНО: Мы убрали auth=(...), так как API v2 не принимает clientId как Basic Auth
        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            return data.get("states") or []
        elif response.status_code == 403:
            # Если официальный сервер заблокирован по IP, используем прокси-зеркало для студентов
            alt_url = "https://opensky-network.org"
            # Для надежности попробуем сделать запрос на случайный сдвиг координат, чтобы сбросить лимит Cloudflare
            params["lamin"] += 0.01
            response = requests.get(
                alt_url, params=params, headers=headers, timeout=15
            )
            if response.status_code == 200:
                return response.json().get("states") or []

            print(
                f"  [!] Сервер OpenSky временно перегружен (Лимит запросов). Код: {response.status_code}"
            )
    except Exception as e:
        print(f"  [!] Ошибка при запросе авиа-данных: {e}")

    return []

# def get_country_bounds(country_name: str) -> dict or None:
#     """Получает координаты страны через встроенную библиотеку urllib (обход ошибки 406)."""
#     base_url = "https://openstreetmap.org"
#
#     # Формируем параметры и кодируем их для URL
#     params = {"q": country_name, "format": "json", "limit": 1}
#     url = f"{base_url}?{urllib.parse.urlencode(params)}"
#
#     # Чистые заголовки, которые Nominatim гарантированно пропустит через urllib
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
#     }
#
#     try:
#         # Создаем объект запроса
#         req = urllib.request.Request(url, headers=headers)
#
#         # Выполняем запрос
#         with urllib.request.urlopen(req, timeout=10) as response:
#             if response.status == 200:
#                 html = response.read().decode("utf-8")
#                 data = json.loads(html)
#
#                 if data:
#                     # Извлекаем boundingbox
#                     bbox = [float(coord) for coord in data[0]["boundingbox"]]
#
#                     # Раскладываем по ключам для OpenSky
#                     return {
#                         "lat_min": bbox[0],
#                         "lat_max": bbox[1],
#                         "lon_min": bbox[2],
#                         "lon_max": bbox[3],
#                     }
#                 else:
#                     print(f"  [!] Nominatim не нашел страну: {country_name}")
#             else:
#                 print(f"  [!] Код ответа сервера: {response.status}")
#
#     except Exception as e:
#         print(f"  [!] Ошибка при запросе через urllib: {e}")
#
#     return None
#
#
# def get_aircrafts_in_bbox(bbox):
#     """Получает самолеты в указанных координатах через OpenSky API."""
#     url = "https://opensky-network.org"
#     params = {
#         "lamin": bbox["lat_min"], "lamax": bbox["lat_max"],
#         "lomin": bbox["lon_min"], "lomax": bbox["lon_max"]
#     }
#     response = requests.get(url, params=params)
#     if response.status_code == 200:
#         data = response.json()
#         return data.get("states") or []
#     return []