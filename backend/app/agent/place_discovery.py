
import os
import time
import math

from dotenv import load_dotenv

from app.integrations.amap.client import AmapClient


CANDIDATE_KEYWORDS = [
    "雷峰塔",
    "岳王庙",
    "浙江省博物馆",
    "中国湿地博物馆",
    "杭州植物园",
    "河坊街",
]

# 杭州市中心参考坐标（GCJ-02）
HANGZHOU_CENTER = (120.1551, 30.2741)

# 当前杭州主城区旅行测试使用的搜索半径
MAX_DISTANCE_KM = 80


def calculate_distance_km(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
) -> float:
    """计算两个坐标之间的直线距离，单位 km。"""

    radius = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * radius * math.asin(
        min(1.0, math.sqrt(a))
    )


def normalize_name(name: str, city: str) -> str:
    """统一地点名称，去掉空格和城市前缀。"""

    result = "".join(name.split())

    if result.startswith(city):
        result = result[len(city):]

    return result


def select_valid_place(
    candidates: list[dict],
    keyword: str,
    city: str,
) -> dict | None:
    """同时检查景点名称和地理位置。"""

    # 当前仅配置杭州主城区的位置范围
    if city != "杭州":
        raise ValueError(
            "当前候选景点位置过滤仅支持杭州"
        )

    center_lon, center_lat = HANGZHOU_CENTER

    for place in candidates:
        name = place.get("name") or ""

        if normalize_name(name, city) != keyword:
            continue

        try:
            longitude = float(place["longitude"])
            latitude = float(place["latitude"])
        except (KeyError, TypeError, ValueError):
            continue

        distance = calculate_distance_km(
            center_lon,
            center_lat,
            longitude,
            latitude,
        )

        if distance > MAX_DISTANCE_KM:
            print(
                f"排除异地地点：{name}，"
                f"距离杭州中心约 {distance:.1f} km"
            )
            continue

        return place

    return None


def discover_places(
    city: str = "杭州",
    existing_names: list[str] | None = None,
) -> list[dict]:
    """查询真实候选景点，避免使用异地 POI。"""

    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        raise ValueError("未配置 AMAP_API_KEY")

    if city != "杭州":
        raise ValueError(
            "当前候选搜索配置仅支持杭州"
        )

    client = AmapClient(api_key=api_key)

    existing_names = set(existing_names or [])

    discovered = []
    seen_ids = set()
    failed_keywords = []

    for keyword in CANDIDATE_KEYWORDS:
        print(f"\n正在搜索：{keyword}")

        try:
            results = client.search_places(
                keywords=keyword,
                city=city,
            )

        except Exception as exc:
            message = str(exc)

            # 遇到频率限制，停止后续请求
            if "CUQPS_HAS_EXCEEDED_THE_LIMIT" in message:
                raise RuntimeError(
                    "高德地图调用频率受限，"
                    "已停止后续请求，避免继续触发限制"
                ) from exc

            print(f"搜索失败：{keyword}，{message}")
            failed_keywords.append(keyword)
            continue

        matched = select_valid_place(
            candidates=results,
            keyword=keyword,
            city=city,
        )

        if matched is None:
            print(f"未找到符合地理范围的地点：{keyword}")
            failed_keywords.append(keyword)

        else:
            poi_id = matched.get("poi_id")
            name = matched.get("name")

            if (
                poi_id
                and poi_id not in seen_ids
                and name not in existing_names
            ):
                seen_ids.add(poi_id)

                discovered.append({
                    "name": name,
                    "poi_id": poi_id,
                    "address": matched.get("address"),
                    "longitude": matched["longitude"],
                    "latitude": matched["latitude"],
                    "city": city,
                    "source": "amap",
                })

                print(f"匹配成功：{name}")

        # 降低连续调用频率
        time.sleep(1.5)

    print("\n搜索结束")
    print("有效候选景点：", len(discovered))
    print("未成功匹配：", failed_keywords)

    return discovered
