
import json
import os
from datetime import time

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.state import TripPlanState
from app.agent.itinerary import GeneratedPlan
from app.agent.quality import check_itinerary_quality


MAX_RETRIES = 2


def repair_itinerary(state: TripPlanState) -> dict:
    """根据质量警告修正行程，不增加未经核实的景点。"""

    retry_count = state.get("retry_count", 0)
    itinerary = state.get("itinerary", [])
    requirements = state.get("parsed_requirements", {})
    warnings = state.get("quality_warnings", [])

    if not itinerary or not requirements:
        return {
            "status": "failed",
            "error_message": "缺少原始行程或旅行需求",
        }

    if state.get("quality_passed") is True:
        return {
            "status": "quality_checked",
            "error_message": None,
        }

    if retry_count >= MAX_RETRIES:
        return {
            "status": "quality_needs_improvement",
            "error_message": "已达到最大修正次数",
        }

    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL")

    if not all([api_key, base_url, model_name]):
        return {
            "status": "failed",
            "error_message": "大模型配置不完整",
        }

    system_prompt = """
你是 TripMate AI 的旅行行程修正助手。

任务：根据质量检查警告，修改已经生成的旅行行程。

必须遵守：
1. 保留所有原有旅行日期和天数。
2. 保留每一天的全部原有景点及顺序。
3. 不允许增加、删除、替换景点。
4. 不允许将景点移动到其他日期。
5. 可以修改活动开始时间、结束时间和游玩描述。
6. 单个景点连续游玩原则上不超过5小时。
7. 不允许出现活动时间重叠。
8. 每天活动必须在用户规定的时间范围内。
9. 不要编造景区开放时间、票价或交通耗时。
10. 无法解决的问题不能通过增加虚假景点来掩盖。

请仅返回合法 JSON，不要返回 Markdown。

JSON 结构：
{
  "title": "旅行标题",
  "destination": "目的地",
  "days": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "theme": "当天主题",
      "activities": [
        {
          "start_time": "09:00",
          "end_time": "12:00",
          "place_name": "原有景点名称",
          "description": "修正后的游玩建议",
          "transport_suggestion": "交通建议"
        }
      ]
    }
  ]
}
"""

    payload = {
        "requirements": requirements,
        "current_itinerary": itinerary,
        "quality_warnings": warnings,
    }

    next_retry = retry_count + 1

    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
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
            raise ValueError("模型没有返回文本")

        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        plan = GeneratedPlan.model_validate_json(content)

        if len(plan.days) != len(itinerary):
            raise ValueError("修正后旅行天数发生变化")

        daily_start = time.fromisoformat(
            requirements["daily_start_time"]
        )
        daily_end = time.fromisoformat(
            requirements["daily_end_time"]
        )

        for old_day, new_day in zip(itinerary, plan.days):
            if (
                new_day.day != old_day["day"]
                or new_day.date != old_day["date"]
            ):
                raise ValueError("修正后旅行日期发生变化")

            old_names = [
                item["place_name"]
                for item in old_day["activities"]
            ]

            new_names = [
                item.place_name
                for item in new_day.activities
            ]

            if old_names != new_names:
                raise ValueError(
                    "修正过程中改变了原有景点或顺序"
                )

            previous_end = None

            for activity in new_day.activities:
                start = time.fromisoformat(
                    activity.start_time
                )
                end = time.fromisoformat(
                    activity.end_time
                )

                if not (
                    daily_start <= start < end <= daily_end
                ):
                    raise ValueError(
                        f"活动时间不合法：{activity.place_name}"
                    )

                if previous_end and start < previous_end:
                    raise ValueError("活动时间存在重叠")

                previous_end = end

        new_itinerary = [
            day.model_dump()
            for day in plan.days
        ]

        # 用原有质量检查器再次检查修正结果
        quality = check_itinerary_quality({
            **state,
            "itinerary": new_itinerary,
        })

        return {
            "itinerary": new_itinerary,
            "retry_count": next_retry,
            "quality_passed": quality["quality_passed"],
            "quality_warnings": quality["quality_warnings"],
            "quality_score": quality["quality_score"],
            "status": (
                "quality_checked"
                if quality["quality_passed"]
                else "quality_needs_improvement"
            ),
            "error_message": None,
        }

    except Exception as exc:
        return {
            "retry_count": next_retry,
            "status": "quality_needs_improvement",
            "error_message": (
                f"第{next_retry}次修正失败："
                f"{type(exc).__name__}: {exc}"
            ),
        }
