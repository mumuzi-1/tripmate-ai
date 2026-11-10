
from datetime import datetime

from app.agent.state import TripPlanState


def check_itinerary_quality(
    state: TripPlanState,
) -> dict:
    """检查 AI 行程是否存在明显的安排问题。"""

    itinerary = state.get("itinerary", [])
    requirements = state.get("parsed_requirements", {})

    if not itinerary:
        return {
            "quality_passed": False,
            "quality_warnings": ["行程内容为空"],
            "quality_score": 0,
        }

    warnings = []
    total_activities = 0

    for day in itinerary:
        day_number = day.get("day")
        activities = day.get("activities", [])

        if not activities:
            warnings.append(
                f"第{day_number}天没有安排任何景点活动"
            )
            continue

        total_activities += len(activities)

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

                duration = (
                    end_time - start_time
                ).total_seconds() / 3600

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

            except (KeyError, TypeError, ValueError):
                warnings.append(
                    f"第{day_number}天的{place_name}"
                    "时间格式不正确"
                )

    total_days = requirements.get(
        "total_days", len(itinerary)
    )

    if total_days and total_activities < total_days:
        warnings.append(
            "整体景点安排较少，"
            "建议根据旅行偏好补充候选景点"
        )

    # 简单的启发式评分，并非真实旅行体验评分
    score = max(0, 100 - len(warnings) * 15)

    return {
        "quality_passed": len(warnings) == 0,
        "quality_warnings": warnings,
        "quality_score": score,
    }
