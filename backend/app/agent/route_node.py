
from app.agent.state import TripPlanState
from app.agent.route_validator import validate_route_times
from app.agent.candidate_filter import calculate_distance_km

from app.integrations.amap.route_service import (
    get_walking_route,
)
from app.integrations.amap.transit_service import (
    get_transit_route,
)


MAX_ROUTE_REQUESTS = 3
WALKING_FALLBACK_KM = 2.0

RATE_LIMIT_CODES = (
    "CUQPS_HAS_EXCEEDED_THE_LIMIT",
    "DAILY_QUERY_OVER_LIMIT",
    "USER_DAILY_QUERY_OVER_LIMIT",
    "ACCESS_TOO_FREQUENT",
)


def is_rate_limit_error(message: str) -> bool:
    return any(code in message for code in RATE_LIMIT_CODES)


def can_fallback_to_walking(message: str) -> bool:
    """只有公交没有可用方案时才回退步行。"""
    return (
        "高德未返回可用公交方案" in message
        or "公交方案缺少有效耗时数据" in message
    )


def check_routes_node(state: TripPlanState) -> dict:
    """查询相邻景点交通路线，并校验时间安排。"""

    itinerary = state.get("itinerary", [])

    if not itinerary:
        return {
            "status": "route_validation_failed",
            "route_validation_passed": False,
            "route_data": [],
            "route_checks": [],
            "route_warnings": ["缺少旅行行程"],
            "route_requests_used": 0,
        }

    all_places = state.get("all_places") or (
        state.get("places", [])
        + state.get("additional_places", [])
    )

    place_lookup = {
        p["name"]: p
        for p in all_places
        if p.get("name")
    }

    requirements = state.get("parsed_requirements", {})
    city = requirements.get("destination", "")
    preference = requirements.get(
        "transport_preference", "public_transport"
    )

    route_pairs = []

    for day in itinerary:
        activities = day.get("activities", [])

        for previous, current in zip(
            activities, activities[1:]
        ):
            route_pairs.append((
                previous["place_name"],
                current["place_name"],
            ))

    if not route_pairs:
        return {
            "status": "route_not_applicable",
            "route_validation_passed": None,
            "route_data": [],
            "route_checks": [],
            "route_warnings": [
                "没有需要校验的同日交通路线"
            ],
            "route_requests_used": 0,
        }

    route_data = list(state.get("route_data", []))

    known_pairs = {
        (
            route["origin_name"],
            route["destination_name"],
        )
        for route in route_data
        if (
            route.get("origin_name")
            and route.get("destination_name")
            and route.get("duration_min") is not None
        )
    }

    requests_used = 0
    fetch_warnings = []
    unique_pairs = list(dict.fromkeys(route_pairs))

    for origin_name, destination_name in unique_pairs:
        pair = (origin_name, destination_name)

        if pair in known_pairs:
            continue

        if requests_used >= MAX_ROUTE_REQUESTS:
            fetch_warnings.append(
                "已达到本次地图路线请求上限"
            )
            break

        origin = place_lookup.get(origin_name)
        destination = place_lookup.get(destination_name)

        if not origin or not destination:
            fetch_warnings.append(
                f"缺少景点坐标：{origin_name} -> "
                f"{destination_name}"
            )
            continue

        try:
            lon1 = float(origin["longitude"])
            lat1 = float(origin["latitude"])
            lon2 = float(destination["longitude"])
            lat2 = float(destination["latitude"])

            if not (
                -180 <= lon1 <= 180
                and -90 <= lat1 <= 90
                and -180 <= lon2 <= 180
                and -90 <= lat2 <= 90
            ):
                raise ValueError("经纬度超出有效范围")

            straight_distance = calculate_distance_km(
                lon1, lat1, lon2, lat2
            )

        except (KeyError, TypeError, ValueError) as exc:
            fetch_warnings.append(
                f"坐标无效：{origin_name} -> "
                f"{destination_name}：{exc}"
            )
            continue

        print(
            f"正在查询交通路线："
            f"{origin_name} -> {destination_name}",
            flush=True,
        )

        result = None

        try:
            # 用户明确选择步行
            if preference == "walking":
                requests_used += 1

                result = get_walking_route(
                    origin_lon=lon1,
                    origin_lat=lat1,
                    destination_lon=lon2,
                    destination_lat=lat2,
                )

            # 用户偏好公共交通
            elif preference == "public_transport":
                if not city:
                    raise ValueError("缺少目的地城市")

                # 公交接口无方案时，短途允许步行降级
                # 距离是直线距离，仅用于决定是否尝试步行
                # 实际步行耗时仍由高德路线接口提供
                if (
                    straight_distance <= WALKING_FALLBACK_KM
                    and requests_used < MAX_ROUTE_REQUESTS
                ):
                    try:
                        requests_used += 1

                        result = get_transit_route(
                            origin_lon=lon1,
                            origin_lat=lat1,
                            destination_lon=lon2,
                            destination_lat=lat2,
                            city=city,
                        )

                    except Exception as transit_exc:
                        message = str(transit_exc)

                        if (
                            can_fallback_to_walking(message)
                            and requests_used < MAX_ROUTE_REQUESTS
                        ):
                            print(
                                "公交无可用方案，尝试步行路线",
                                flush=True,
                            )

                            requests_used += 1

                            result = get_walking_route(
                                origin_lon=lon1,
                                origin_lat=lat1,
                                destination_lon=lon2,
                                destination_lat=lat2,
                            )
                        else:
                            raise

                else:
                    requests_used += 1

                    result = get_transit_route(
                        origin_lon=lon1,
                        origin_lat=lat1,
                        destination_lon=lon2,
                        destination_lat=lat2,
                        city=city,
                    )

            else:
                fetch_warnings.append(
                    f"暂不支持交通方式：{preference}"
                )
                continue

            if result is None:
                raise RuntimeError("没有获得路线结果")

            route_data.append({
                "origin_name": origin_name,
                "destination_name": destination_name,
                "transport_mode": result["transport_mode"],
                "duration_min": result["duration_min"],
                "source": result["source"],
                "details": result,
            })

            known_pairs.add(pair)

        except Exception as exc:
            message = str(exc)

            fetch_warnings.append(
                f"路线查询失败："
                f"{origin_name} -> {destination_name}："
                f"{message}"
            )

            if is_rate_limit_error(message):
                break

    validation = validate_route_times(
        state=state,
        route_data=route_data,
        buffer_minutes=15,
    )

    checks = validation["route_checks"]

    if any(
        check["status"] == "unknown"
        for check in checks
    ):
        status = "route_needs_data"

    elif not validation["route_validation_passed"]:
        status = "route_conflict"

    else:
        status = "route_checked"

    warnings = (
        validation["route_warnings"]
        + fetch_warnings
    )

    return {
        **validation,
        "route_data": route_data,
        "route_requests_used": requests_used,
        "route_warnings": warnings,
        "status": status,
    }
