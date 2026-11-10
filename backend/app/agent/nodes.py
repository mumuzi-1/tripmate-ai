
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select

from app.agent.state import TripPlanState
from app.core.database import SessionLocal
from app.models.trip import Trip
from app.models.trip_requirement import TripRequirement


def serialize_value(value: Any) -> Any:
    """将日期、时间等转换为可序列化的数据。"""

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, dict):
        return {
            key: serialize_value(item)
            for key, item in value.items()
        }

    return value


def load_requirements(
    state: TripPlanState,
) -> dict:
    """从 MySQL 加载当前用户的旅行需求。"""

    trip_id = state.get("trip_id")
    user_id = state.get("user_id")

    if trip_id is None or user_id is None:
        return {
            "status": "failed",
            "error_message": "缺少旅行 ID 或用户 ID",
        }

    with SessionLocal() as db:
        trip = db.scalar(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id,
            )
        )

        if trip is None:
            return {
                "status": "failed",
                "error_message": "旅行不存在或无权访问",
            }

        requirement = db.scalar(
            select(TripRequirement).where(
                TripRequirement.trip_id == trip_id
            )
        )

        if requirement is None:
            return {
                "status": "failed",
                "error_message": "该旅行尚未填写旅行需求",
            }

        fields = [
            "departure_city",
            "start_date",
            "end_date",
            "travelers",
            "travel_style",
            "travel_pace",
            "transport_preference",
            "accommodation_preference",
            "daily_start_time",
            "daily_end_time",
            "must_visit_places",
            "excluded_places",
            "preferred_activities",
            "special_requirements",
        ]

        requirements = {
            field: serialize_value(
                getattr(requirement, field)
            )
            for field in fields
        }

        requirements["destination"] = trip.destination
        requirements["trip_title"] = trip.title

        return {
            "requirements": requirements,
            "status": "requirements_loaded",
            "error_message": None,
        }

def parse_requirements(
    state: TripPlanState,
) -> dict:
    """解析旅行需求，生成标准化规划约束。"""

    requirements = state.get("requirements")

    if not requirements:
        return {
            "status": "failed",
            "error_message": "旅行需求为空，无法进行规划",
        }

    try:
        start_date = date.fromisoformat(
            requirements["start_date"]
        )

        end_date = date.fromisoformat(
            requirements["end_date"]
        )

        days = (end_date - start_date).days + 1

        if days <= 0:
            raise ValueError("旅行日期不合法")

        daily_start = time.fromisoformat(
            requirements["daily_start_time"]
        )

        daily_end = time.fromisoformat(
            requirements["daily_end_time"]
        )

        if daily_end <= daily_start:
            raise ValueError("每日游玩时间不合法")

        parsed_requirements = {
            "trip_title": requirements["trip_title"],
            "departure_city": requirements["departure_city"],
            "destination": requirements["destination"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": days,
            "travelers": requirements["travelers"],
            "travel_style": requirements["travel_style"],
            "travel_pace": requirements["travel_pace"],
            "transport_preference": requirements[
                "transport_preference"
            ],
            "accommodation_preference": requirements.get(
                "accommodation_preference"
            ),
            "daily_start_time": daily_start.isoformat(),
            "daily_end_time": daily_end.isoformat(),
            "must_visit_places": requirements.get(
                "must_visit_places", []
            ),
            "excluded_places": requirements.get(
                "excluded_places", []
            ),
            "preferred_activities": requirements.get(
                "preferred_activities", []
            ),
            "special_requirements": requirements.get(
                "special_requirements"
            ),
        }

        return {
            "parsed_requirements": parsed_requirements,
            "status": "requirements_parsed",
            "error_message": None,
        }

    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "failed",
            "error_message": f"旅行需求解析失败：{exc}",
        }

import os

from dotenv import load_dotenv

from app.integrations.amap.client import AmapClient


# 常见景点名称映射
PLACE_NAME_MAPPING = {
    "西湖": "西湖风景名胜区",
    "灵隐寺": "灵隐寺",
    "西溪湿地": "西溪国家湿地公园",
}


def normalize_place_name(name: str, city: str) -> str:
    """去除空格及城市前缀，用于地点名称匹配。"""

    normalized = "".join(name.split())

    if normalized.startswith(city):
        normalized = normalized[len(city):]

    return normalized


def search_places(
    state: TripPlanState,
) -> dict:
    """通过高德地图搜索旅行必去景点。"""

    parsed = state.get("parsed_requirements")

    if not parsed:
        return {
            "status": "failed",
            "error_message": "缺少已解析的旅行需求",
        }

    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        return {
            "status": "failed",
            "error_message": "未配置高德地图 API Key",
        }

    client = AmapClient(api_key=api_key)

    city = parsed["destination"]
    must_visit = parsed.get("must_visit_places", [])
    excluded = parsed.get("excluded_places", [])

    # 不允许把明确排除的地点加入规划
    if set(must_visit) & set(excluded):
        return {
            "status": "failed",
            "error_message": "必去景点与排除景点存在冲突",
        }

    matched_places = []
    unmatched_places = []

    for name in must_visit:
        keyword = PLACE_NAME_MAPPING.get(name, name)

        try:
            candidates = client.search_places(
                keywords=keyword,
                city=city,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "error_message": (
                    f"搜索{name}失败：{type(exc).__name__}: {exc}"
                ),
            }

        expected_name = normalize_place_name(
            keyword,
            city,
        )

        # 只接受名称精确匹配的候选地点
        # 避免把西湖附近的餐厅、停车场等误选为西湖
        matched = None

        for candidate in candidates:
            candidate_name = normalize_place_name(
                candidate.get("name") or "",
                city,
            )

            if candidate_name == expected_name:
                matched = candidate
                break

        if matched is None:
            unmatched_places.append(name)
            continue

        matched_places.append({
            "original_name": name,
            "name": matched["name"],
            "address": matched.get("address"),
            "poi_id": matched.get("poi_id"),
            "longitude": matched["longitude"],
            "latitude": matched["latitude"],
            "city": city,
        })

    if unmatched_places:
        return {
            "places": matched_places,
            "status": "failed",
            "error_message": (
                "以下地点未找到准确匹配结果："
                + "、".join(unmatched_places)
            ),
        }

    return {
        "places": matched_places,
        "status": "places_loaded",
        "error_message": None,
    }
