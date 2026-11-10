
import os
import httpx

from dotenv import load_dotenv


def get_walking_route(
    origin_lon: float,
    origin_lat: float,
    destination_lon: float,
    destination_lat: float,
) -> dict:
    """调用高德地图 API 查询真实步行路线。"""

    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        raise ValueError("未配置 AMAP_API_KEY")

    url = "https://restapi.amap.com/v3/direction/walking"

    params = {
        "key": api_key,
        "origin": f"{origin_lon:.6f},{origin_lat:.6f}",
        "destination": (
            f"{destination_lon:.6f},{destination_lat:.6f}"
        ),
        "output": "JSON",
    }

    with httpx.Client(timeout=20.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "1":
        raise RuntimeError(
            "高德路线查询失败："
            + str(data.get("info", "未知错误"))
        )

    paths = data.get("route", {}).get("paths", [])

    if not paths:
        raise RuntimeError("高德未返回可用步行路线")

    path = paths[0]

    distance_m = int(path["distance"])
    duration_s = int(path["duration"])

    if distance_m < 0 or duration_s < 0:
        raise ValueError("路线距离或时间无效")

    return {
        "transport_mode": "walking",
        "distance_m": distance_m,
        "duration_s": duration_s,
        "distance_km": round(distance_m / 1000, 2),
        "duration_min": round(duration_s / 60, 1),
        "source": "amap",
    }
