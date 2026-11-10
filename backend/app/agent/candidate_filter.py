
import math
from statistics import median


# 初期测试的候选地点搜索范围，单位 km
DEFAULT_RADIUS_KM = 40.0


def calculate_distance_km(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
) -> float:
    """计算两个坐标间的直线距离。"""

    radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * radius * math.asin(
        min(1.0, math.sqrt(a))
    )


def normalize_name(name: str, city: str) -> str:
    """统一地点名称格式。"""

    result = "".join(name.split())

    for prefix in (
        city,
        city + "市",
    ):
        if result.startswith(prefix):
            result = result[len(prefix):]
            break

    return result


def get_reference_center(
    verified_places: list[dict],
) -> tuple[float, float]:
    """根据已核实景点计算旅行区域的参考中心。"""

    if not verified_places:
        raise ValueError("缺少已核实的参考景点")

    longitudes = [
        float(p["longitude"])
        for p in verified_places
    ]

    latitudes = [
        float(p["latitude"])
        for p in verified_places
    ]

    return (
        median(longitudes),
        median(latitudes),
    )


def filter_candidates(
    city: str,
    candidates: list[dict],
    verified_places: list[dict],
    excluded_names: list[str] | None = None,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> list[dict]:
    """根据地理位置、排除名单和 POI ID 筛选候选地点。"""

    if radius_km <= 0:
        raise ValueError("搜索半径必须大于0")

    center_lon, center_lat = get_reference_center(
        verified_places
    )

    excluded_names = excluded_names or []

    blocked_names = {
        normalize_name(name, city)
        for name in excluded_names
    }

    verified_ids = {
        p.get("poi_id")
        for p in verified_places
        if p.get("poi_id")
    }

    verified_names = {
        normalize_name(p.get("name") or "", city)
        for p in verified_places
    }

    selected = []
    seen_ids = set()
    seen_names = set()

    for place in candidates:
        name = place.get("name") or ""
        poi_id = place.get("poi_id")

        normalized_name = normalize_name(name, city)

        if not normalized_name or not poi_id:
            continue

        # 排除用户不想去的地点
        if normalized_name in blocked_names:
            continue

        # 排除已经确认的必去景点
        if (
            poi_id in verified_ids
            or normalized_name in verified_names
        ):
            continue

        # 去除候选地点重复项
        if (
            poi_id in seen_ids
            or normalized_name in seen_names
        ):
            continue

        try:
            lon = float(place["longitude"])
            lat = float(place["latitude"])
        except (KeyError, TypeError, ValueError):
            continue

        # 检查坐标是否有效
        if not (
            -180 <= lon <= 180
            and -90 <= lat <= 90
        ):
            continue

        distance = calculate_distance_km(
            center_lon,
            center_lat,
            lon,
            lat,
        )

        # 排除距离旅行区域过远的候选地点
        if distance > radius_km:
            continue

        selected.append({
            **place,
            "distance_from_center_km": round(
                distance, 2
            ),
        })

        seen_ids.add(poi_id)
        seen_names.add(normalized_name)

    return selected
