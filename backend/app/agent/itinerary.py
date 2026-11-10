
import json
import os

from datetime import date, time, timedelta

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agent.state import TripPlanState


class VisitItem(BaseModel):
    """单个景点活动"""

    start_time: str
    end_time: str
    place_name: str
    description: str
    transport_suggestion: str


class DayPlan(BaseModel):
    """单日旅行计划"""

    day: int
    date: str
    theme: str
    activities: list[VisitItem] = Field(default_factory=list)


class GeneratedPlan(BaseModel):
    """完整旅行计划"""

    title: str
    destination: str
    days: list[DayPlan]


def generate_itinerary(state: TripPlanState) -> dict:
    """根据必去景点和已核验的可选景点生成行程。"""

    requirements = state.get("parsed_requirements", {})

    # 用户必去景点
    required_places = state.get("places", [])

    # 高德核验通过的补充景点
    optional_places = state.get("additional_places", [])

    if not requirements:
        return {
            "status": "failed",
            "validation_passed": False,
            "error_message": "缺少已解析的旅行需求",
        }

    if not required_places:
        return {
            "status": "failed",
            "validation_passed": False,
            "error_message": "缺少已核验的必去景点",
        }

    # 去重，确保补充地点不重复必去景点
    required_names = {
        place["name"]
        for place in required_places
    }

    optional_unique = []
    seen_names = set(required_names)

    for place in optional_places:
        name = place.get("name")

        if not name or name in seen_names:
            continue

        if not place.get("verified", False):
            continue

        if not place.get("poi_id"):
            continue

        optional_unique.append(place)
        seen_names.add(name)

    all_places = required_places + optional_unique

    allowed_names = {
        place["name"]
        for place in all_places
    }

    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL")

    if not all([api_key, base_url, model_name]):
        return {
            "status": "failed",
            "validation_passed": False,
            "error_message": "大模型配置不完整",
        }

    system_prompt = """
你是 TripMate AI 的旅行行程规划 Agent。

请根据用户旅行需求及已核验的真实地点，生成每日旅行行程。

【地点规则】
1. 必去景点必须全部安排。
2. 补充景点是可选的，不要求全部安排。
3. 只能使用提供的真实 POI 名称。
4. 不允许编造额外地点。
5. 不允许安排用户排除的景点。
6. 同一个景点不要重复安排。

【时间规则】
1. 必须生成与旅行日期一致的每日行程。
2. 每天活动必须处于用户规定的游玩时间范围内。
3. 不允许活动时间重叠。
4. 单个景点连续游览建议不超过5小时。
5. 不要求每天从早到晚排满活动。
6. 根据旅行节奏合理安排休息和空闲时间。

【路线规则】
1. 优先把地理位置相近的景点安排在同一天。
2. 尽量减少跨区域往返。
3. 考虑用户的交通方式偏好。
4. 交通建议可以提供一般方式，但不能编造已核实的线路和耗时。

【真实性规则】
1. 景点坐标来自地图数据。
2. 开放时间、门票及实时路况尚未核验。
3. 不得把未经核实的信息描述为已确认事实。

【输出要求】
只输出合法 JSON，不要输出 Markdown 或额外解释。

JSON 格式：
{
  "title": "旅行标题",
  "destination": "目的地",
  "days": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "theme": "当日主题",
      "activities": [
        {
          "start_time": "09:00",
          "end_time": "11:00",
          "place_name": "真实 POI 名称",
          "description": "具体游玩建议",
          "transport_suggestion": "一般交通建议"
        }
      ]
    }
  ]
}
"""

    payload = {
        "requirements": requirements,
        "required_places": [
            {
                "name": p["name"],
                "longitude": p["longitude"],
                "latitude": p["latitude"],
                "address": p.get("address"),
                "required": True,
            }
            for p in required_places
        ],
        "optional_places": [
            {
                "name": p["name"],
                "longitude": p["longitude"],
                "latitude": p["latitude"],
                "address": p.get("address"),
                "required": False,
            }
            for p in optional_unique
        ],
    }

    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.2,
            timeout=120,
            max_retries=1,
        )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            ),
        ])

        content = response.content

        if not isinstance(content, str):
            raise ValueError("模型未返回文本内容")

        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()

            content = "\n".join(
                line
                for line in lines
                if not line.strip().startswith("```")
            ).strip()

        plan = GeneratedPlan.model_validate_json(content)

        expected_days = requirements["total_days"]

        if len(plan.days) != expected_days:
            raise ValueError("生成的旅行天数不正确")

        if plan.destination != requirements["destination"]:
            raise ValueError("生成的旅行目的地不正确")

        start_date = date.fromisoformat(
            requirements["start_date"]
        )

        daily_start = time.fromisoformat(
            requirements["daily_start_time"]
        )

        daily_end = time.fromisoformat(
            requirements["daily_end_time"]
        )

        used_names = set()

        excluded_names = set(
            requirements.get("excluded_places", [])
        )

        for index, day_plan in enumerate(plan.days):
            expected_date = (
                start_date + timedelta(days=index)
            ).isoformat()

            if day_plan.day != index + 1:
                raise ValueError("行程序号不正确")

            if day_plan.date != expected_date:
                raise ValueError("行程日期不正确")

            previous_end = None

            for activity in day_plan.activities:
                name = activity.place_name

                # 地点必须来自高德核验结果
                if name not in allowed_names:
                    raise ValueError(
                        f"存在未经核验的地点：{name}"
                    )

                if name in excluded_names:
                    raise ValueError(
                        f"包含用户排除的地点：{name}"
                    )

                if name in used_names:
                    raise ValueError(
                        f"景点重复安排：{name}"
                    )

                used_names.add(name)

                activity_start = time.fromisoformat(
                    activity.start_time
                )

                activity_end = time.fromisoformat(
                    activity.end_time
                )

                if not (
                    daily_start
                    <= activity_start
                    < activity_end
                    <= daily_end
                ):
                    raise ValueError(
                        f"活动时间不合法：{name}"
                    )

                if (
                    previous_end is not None
                    and activity_start < previous_end
                ):
                    raise ValueError(
                        f"第{day_plan.day}天活动时间重叠"
                    )

                previous_end = activity_end

        # 只强制检查用户必去景点
        missing_required = required_names - used_names

        if missing_required:
            raise ValueError(
                "必去景点未全部安排："
                + "、".join(sorted(missing_required))
            )

        # 补充景点允许只使用一部分
        optional_used = used_names - required_names

        return {
            "itinerary": [
                day.model_dump()
                for day in plan.days
            ],
            "status": "itinerary_generated",
            "validation_passed": True,
            "validation_errors": [],
            "error_message": None,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "validation_passed": False,
            "validation_errors": [str(exc)],
            "error_message": (
                "AI 行程生成或校验失败："
                f"{type(exc).__name__}: {exc}"
            ),
        }
