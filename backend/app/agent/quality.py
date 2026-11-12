
from datetime import datetime

from app.agent.state import TripPlanState


def check_itinerary_quality(
    state: TripPlanState,
) -> dict:
    """检查 AI 行程的时间安排、天数及活动合理性。"""

    itinerary = state.get("itinerary", []) or []
    requirements = state.get("parsed_requirements", {}) or {}

    if not itinerary:
        return {
            "quality_passed": False,
            "quality_warnings": ["行程内容为空"],
            "quality_score": 0,
        }

    warnings = []
    total_activities = 0
    day_numbers = []

    # 1. 检查每一天的活动安排
    for day in itinerary:
        day_number = day.get("day")
        activities = day.get("activities", []) or []

        day_numbers.append(day_number)

        if not activities:
            warnings.append(
                f"第{day_number}天没有安排任何景点活动"
            )
            continue

        total_activities += len(activities)

        # 保存当天有效活动的时间区间
        time_ranges = []

        for activity in activities:
            place_name = activity.get(
                "place_name", "未知地点"
            )

            try:
                start_time = datetime.strptime(
                    activity["start_time"], "%H:%M"
                )

                end_time = datetime.strptime(
                    activity["end_time"], "%H:%M"
                )

            except (KeyError, TypeError, ValueError):
                warnings.append(
                    f"第{day_number}天的{place_name}"
                    "时间格式不正确"
                )
                continue

            # 2. 检查时间倒序
            if end_time <= start_time:
                warnings.append(
                    f"第{day_number}天的{place_name}"
                    "结束时间不能早于或等于开始时间"
                )
                continue

            duration = (
                end_time - start_time
            ).total_seconds() / 3600

            # 3. 检查单项活动时长
            if duration > 5:
                warnings.append(
                    f"第{day_number}天的{place_name}"
                    f"连续安排{duration:g}小时，"
                    "建议核实实际游玩时长并优化"
                )

            if duration < 0.5:
                warnings.append(
                    f"第{day_number}天的{place_name}"
                    "游玩时间不足30分钟"
                )

            time_ranges.append(
                (start_time, end_time, place_name)
            )

        # 4. 检查同一天的活动时间重叠
        time_ranges.sort(key=lambda item: item[0])

        for index in range(1, len(time_ranges)):
            previous_start, previous_end, previous_name = (
                time_ranges[index - 1]
            )

            current_start, current_end, current_name = (
                time_ranges[index]
            )

            if current_start < previous_end:
                warnings.append(
                    f"第{day_number}天的"
                    f"{previous_name}与{current_name}"
                    "活动时间存在重叠"
                )

    # 5. 检查旅行天数
    total_days = requirements.get(
        "total_days", len(itinerary)
    )

    if isinstance(total_days, int) and total_days > 0:
        if len(itinerary) != total_days:
            warnings.append(
                f"计划旅行{total_days}天，"
                f"实际生成{len(itinerary)}天，"
                "旅行天数不一致"
            )

        if total_activities < total_days:
            warnings.append(
                "整体景点安排较少，"
                "建议根据旅行偏好补充候选景点"
            )

        expected_days = set(range(1, total_days + 1))

        if (
            all(
                type(number) is int
                for number in day_numbers
            )
            and set(day_numbers) != expected_days
        ):
            warnings.append(
                "行程日期编号存在缺失、"
                "重复或超出旅行天数"
            )

    # 6. 检查重复日期编号
    # 避免缺失、重复日期导致部分行程被覆盖
    if len(set(map(str, day_numbers))) != len(day_numbers):
        if not any(
            "行程日期编号" in warning
            for warning in warnings
        ):
            warnings.append(
                "行程日期编号存在重复"
            )

    # 7. 启发式质量评分
    # 注意：该评分不代表真实旅行体验
    score = max(
        0,
        100 - len(warnings) * 15
    )

    return {
        "quality_passed": len(warnings) == 0,
        "quality_warnings": warnings,
        "quality_score": score,
    }
