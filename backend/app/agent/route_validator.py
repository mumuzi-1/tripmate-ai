
from datetime import datetime

from app.agent.state import TripPlanState


DEFAULT_BUFFER_MINUTES = 15


def minutes_between(
    start_time: str,
    end_time: str,
) -> float:
    """计算两个 HH:MM 时间之间的分钟数。"""

    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")

    return (end - start).total_seconds() / 60


def validate_route_times(
    state: TripPlanState,
    route_data: list[dict],
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
) -> dict:
    """根据地图路线耗时检查相邻景点的交通时间。"""

    itinerary = state.get("itinerary", [])

    if not itinerary:
        return {
            "route_validation_passed": False,
            "route_warnings": ["旅行行程为空"],
            "route_checks": [],
        }

    if buffer_minutes < 0:
        raise ValueError("交通缓冲时间不能为负数")

    route_lookup = {}

    for route in route_data:
        key = (
            route["origin_name"],
            route["destination_name"],
        )

        route_lookup[key] = route

    warnings = []
    checks = []

    for day in itinerary:
        activities = day.get("activities", [])

        if len(activities) < 2:
            continue

        for previous, current in zip(
            activities,
            activities[1:],
        ):
            origin_name = previous["place_name"]
            destination_name = current["place_name"]

            available_minutes = minutes_between(
                previous["end_time"],
                current["start_time"],
            )

            route = route_lookup.get(
                (origin_name, destination_name)
            )

            if route is None:
                checks.append({
                    "day": day["day"],
                    "origin": origin_name,
                    "destination": destination_name,
                    "status": "unknown",
                    "available_minutes": available_minutes,
                    "route_minutes": None,
                })

                warnings.append(
                    f"第{day['day']}天缺少"
                    f"{origin_name}到{destination_name}"
                    "的地图交通数据"
                )

                continue

            route_minutes = float(
                route["duration_min"]
            )

            required_minutes = (
                route_minutes + buffer_minutes
            )

            enough_time = (
                available_minutes >= required_minutes
            )

            check = {
                "day": day["day"],
                "origin": origin_name,
                "destination": destination_name,
                "transport_mode": route.get(
                    "transport_mode"
                ),
                "available_minutes": round(
                    available_minutes, 1
                ),
                "route_minutes": round(
                    route_minutes, 1
                ),
                "buffer_minutes": buffer_minutes,
                "required_minutes": round(
                    required_minutes, 1
                ),
                "remaining_minutes": round(
                    available_minutes - required_minutes, 1
                ),
                "status": (
                    "passed"
                    if enough_time
                    else "insufficient"
                ),
            }

            checks.append(check)

            if not enough_time:
                shortage = (
                    required_minutes - available_minutes
                )

                warnings.append(
                    f"第{day['day']}天"
                    f"{origin_name}到{destination_name}"
                    f"交通时间不足，缺少{shortage:.1f}分钟"
                )

    return {
        "route_validation_passed": len(warnings) == 0,
        "route_warnings": warnings,
        "route_checks": checks,
    }
