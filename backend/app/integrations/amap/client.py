
import httpx


class AmapClient:
    """高德地图 Web 服务 API 客户端"""

    BASE_URL = "https://restapi.amap.com/v3"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("高德地图 API Key 不能为空")

        self.api_key = api_key

    def search_places(
        self,
        keywords: str,
        city: str,
    ) -> list[dict]:
        """根据关键词搜索真实地点"""

        params = {
            "key": self.api_key,
            "keywords": keywords,
            "city": city,
            "citylimit": "true",
            "offset": 10,
            "page": 1,
            "extensions": "base",
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{self.BASE_URL}/place/text",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "1":
            raise RuntimeError(
                f"高德地图查询失败：{data.get('info', '未知错误')}"
            )

        places = []

        for item in data.get("pois", []):
            location = item.get("location", "")

            if not isinstance(location, str):
                continue

            coordinates = location.split(",")

            if len(coordinates) != 2:
                continue

            try:
                longitude = float(coordinates[0])
                latitude = float(coordinates[1])
            except ValueError:
                continue

            places.append({
                "poi_id": item.get("id"),
                "name": item.get("name"),
                "address": item.get("address"),
                "longitude": longitude,
                "latitude": latitude,
                "type": item.get("type"),
                "city": city,
            })

        return places
