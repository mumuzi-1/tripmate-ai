
from copy import deepcopy
from datetime import datetime, timedelta
from math import ceil

from app.agent.state import TripPlanState
from app.agent.route_validator import validate_route_times


BUFFER_MINUTES = 15


def parse_time(value: str) -> datetime:
    """解析 HH:MM 时间。"""
    return datetime.strptime(value, "%H:%M")


def repair_route_times(state: TripPlanState) -> dict:
    """根据已有地图路线耗时自动调整相邻活动时间。"""

    original = state.get("itinerary", [])
    route_data = state.get("route_data", [])
    requirements = state.get("parsed_requirements", {})

    if not original:
        return {
            "status": "route_repair_failed",
            "error_message": "缺少旅行行程",
            "route_adjustments": [],
        }

    # 先检查已有路线数据
    initial = validate_route_times(
        state=state,
        route_data=route_data,
        buffer_minutes=BUFFER_MINUTES,
    )

    # 存在未查询成功的路线时，不使用猜测耗时修正
    if any(
        check["status"] == "unknown"
        for check in initial["route_checks"]
    ):
        return {
            "status": "route_needs_data",
            "route_validation_passed": False,
            "route_warnings": initial["route_warnings"],
            "route_adjustments": [],
            "error_message": "存在缺少地图数据的交通路线",
        }

    if initial["route_validation_passed"]:
        return {
            "status": "route_checked",
            "itinerary": original,
            "route_validation_passed": True,
            "route_warnings": [],
            "route_checks": initial["route_checks"],
            "route_adjustments": [],
            "error_message": None,
        }

    # 用实际地图数据建立路线查找表
    route_lookup = {
        (
            route["origin_name"],
            route["destination_name"],
        ): route
        for route in route_data
        if route.get("duration_min") is not None
    }

    repaired = deepcopy(original)
    adjustments = []

    try:
        daily_start = parse_time(
            requirements.get(
                "daily_start_time", "00:00:00"
            )[:5]
        )

        daily_end = parse_time(
            requirements.get(
                "daily_end_time", "23:59:00"
            )[:5]
        )

        for day in repaired:
            activities = day.get("activities", [])

            if not activities:
                continue

            first_start = parse_time(
                activities[0]["start_time"]
            )

            if first_start < daily_start:
                raise ValueError(
                    f"第{day['day']}天活动早于允许开始时间"
                )

            for index in range(1, len(activities)):
                previous = activities[index - 1]
                current = activities[index]

                route = route_lookup.get((
                    previous["place_name"],
                    current["place_name"],
                ))

                if route is None:
                    raise ValueError(
                        "缺少地图路线数据："
                        f"{previous['place_name']} -> "
                        f"{current['place_name']}"
                    )

                duration_min = float(
                    route["duration_min"]
                )

                if not 0 <= duration_min < float("inf"):
                    raise ValueError("路线耗时无效")

                # HH:MM 精度下，交通与缓冲时长向上取整
                required_minutes = ceil(
                    duration_min + BUFFER_MINUTES
                )

                previous_end = parse_time(
                    previous["end_time"]
                )

                current_start = parse_time(
                    current["start_time"]
                )

                current_end = parse_time(
                    current["end_time"]
                )

                original_duration = (
                    current_end - current_start
                )

                if original_duration <= timedelta(0):
                    raise ValueError("活动原始时间不合法")

                earliest_start = (
                    previous_end
                    + timedelta(minutes=required_minutes)
                )

                if current_start >= earliest_start:
                    continue

                # 只顺延，不缩短景点原有游览时长
                new_start = earliest_start
                new_end = new_start + original_duration

                if new_end > daily_end:
                    raise ValueError(
                        f"第{day['day']}天的"
                        f"{current['place_name']}顺延后"
                        "超出每日结束时间"
                    )

                old_start = current["start_time"]
                old_end = current["end_time"]

                current["start_time"] = new_start.strftime(
                    "%H:%M"
                )
                current["end_time"] = new_end.strftime(
                    "%H:%M"
                )

                adjustments.append({
                    "day": day["day"],
                    "place_name": current["place_name"],
                    "old_start": old_start,
                    "old_end": old_end,
                    "new_start": current["start_time"],
                    "new_end": current["end_time"],
                    "shift_minutes": int(
                        (new_start - current_start)
                        .total_seconds() / 60
                    ),
                })

        # 修正完成后，再运行原有交通校验器
        validation = validate_route_times(
            state={
                **state,
                "itinerary": repaired,
            },
            route_data=route_data,
            buffer_minutes=BUFFER_MINUTES,
        )

        if not validation["route_validation_passed"]:
            raise ValueError(
                "调整后仍存在交通时间冲突"
            )

        return {
            "status": "route_repaired",
            "itinerary": repaired,
            "route_validation_passed": True,
            "route_warnings": [],
            "route_checks": validation["route_checks"],
            "route_adjustments": adjustments,
            "error_message": None,
        }

    except (ValueError, TypeError, KeyError) as exc:
        # 修正失败时不覆盖原始行程
        return {
            "status": "route_repair_failed",
            "route_validation_passed": False,
            "route_warnings": initial["route_warnings"],
            "route_adjustments": [],
            "error_message": str(exc),
        }
