from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union

import requests


class BaseAPI(ABC):
    """Абстрактный класс для работы с API"""

    @abstractmethod
    def get_country_bbox(self, country: str) -> tuple:
        """Получить bounding box страны"""
        pass

    @abstractmethod
    def get_aeroplanes(self, country: str) -> list:
        """Получить список самолетов в воздушном пространстве страны"""
        pass


class OpenSkyAPI(BaseAPI):
    """Реализация для Nominatim и OpenSky Network"""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OPENSKY_URL = "https://opensky-network.org/api/states/all"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CourseWorkApp/1.0"})

    def get_country_bbox(self, country: str) -> tuple:
        return self._get_country_bbox(country)

    def _get_country_bbox(self, country: str) -> tuple:
        """Внутренний метод для получения bounding box страны"""
        params: Dict[str, Union[str, int]] = {
            "q": country,
            "format": "json",
            "limit": 1
        }
        response = self.session.get(self.NOMINATIM_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise ValueError(f"Страна '{country}' не найдена")
        bbox = data[0]["boundingbox"]
        return tuple(float(coord) for coord in bbox)

    def get_aeroplanes(self, country: str) -> List[Any]:
        """Получить список самолетов в воздушном пространстве страны"""
        bbox = self._get_country_bbox(country)
        south, north, west, east = bbox
        params = {"lamin": south, "lamax": north, "lomin": west, "lomax": east}
        response = self.session.get(self.OPENSKY_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("states", [])