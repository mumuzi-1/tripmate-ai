
import os

import httpx
from dotenv import load_dotenv


def get_transit_route(
    origin_lon: float,
    origin_lat: float,
    destination_lon: float,
    destination_lat: float,
    city: str,
) -> dict:
    """调用高德地图公交换乘 API。"""

    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        raise ValueError("未配置 AMAP_API_KEY")

    url = (
        "https://restapi.amap.com/v3/"
        "direction/transit/integrated"
    )

    params = {
        "key": api_key,
        "origin": f"{origin_lon:.6f},{origin_lat:.6f}",
        "destination": (
            f"{destination_lon:.6f},{destination_lat:.6f}"
        ),
        "city": city,
        "strategy": 0,
        "extensions": "all",
        "output": "JSON",
    }

    with httpx.Client(timeout=25.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "1":
        raise RuntimeError(
            "高德公交查询失败："
            + str(data.get("info", "未知错误"))
        )

    transits = data.get(
        "route", {}
    ).get("transits", [])

    if not transits:
        raise RuntimeError("高德未返回可用公交方案")

    valid_routes = []

    for transit in transits:
        try:
            duration = int(transit["duration"])
            walking_distance = int(
                transit.get("walking_distance") or 0
            )
        except (ValueError, TypeError, KeyError):
            continue

        if duration <= 0:
            continue

        lines = []

        for segment in transit.get("segments", []):
            bus = segment.get("bus") or {}

            for line in bus.get("buslines", []):
                lines.append({
                    "name": line.get("name", ""),
                    "type": line.get("type", ""),
                    "departure_stop": (
                        line.get("departure_stop") or {}
                    ).get("name", ""),
                    "arrival_stop": (
                        line.get("arrival_stop") or {}
                    ).get("name", ""),
                })

        valid_routes.append({
            "duration_s": duration,
            "duration_min": round(duration / 60, 1),
            "walking_distance_m": walking_distance,
            "cost": transit.get("cost"),
            "lines": lines,
        })

    if not valid_routes:
        raise RuntimeError("公交方案缺少有效耗时数据")

    # 选择预计耗时最短的有效方案
    best = min(
        valid_routes,
        key=lambda route: route["duration_s"],
    )

    return {
        "transport_mode": "public_transport",
        "duration_s": best["duration_s"],
        "duration_min": best["duration_min"],
        "walking_distance_m": best["walking_distance_m"],
        "cost": best["cost"],
        "lines": best["lines"],
        "alternative_count": len(valid_routes),
        "source": "amap",
    }
