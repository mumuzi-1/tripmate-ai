
import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agent.state import TripPlanState


class PlaceRecommendation(BaseModel):
    """AI 推荐的候选景点"""

    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    category: str = Field(min_length=1)


class PlaceRecommendationResult(BaseModel):
    """AI 景点推荐结果"""

    candidates: list[PlaceRecommendation]


def normalize_name(name: str) -> str:
    return "".join(name.split()).lower()


def recommend_places(
    state: TripPlanState,
) -> dict:
    """根据旅行需求动态推荐候选景点关键词。"""

    requirements = state.get("parsed_requirements")

    if not requirements:
        return {
            "status": "failed",
            "error_message": "缺少已解析的旅行需求",
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
你是 TripMate AI 的旅行候选景点推荐助手。

根据用户的目的地、旅行天数、旅行风格、
旅行节奏、偏好活动以及必去景点，
提出适合补充到旅行行程中的候选地点。

要求：
1. 推荐6至10个候选地点。
2. 只推荐用户目的地范围内的地点。
3. 不要重复推荐用户已经指定的必去景点。
4. 不能推荐用户明确排除的地点。
5. 优先推荐有明确名称、容易在地图中检索的地点。
6. 根据用户喜好兼顾景点、美食街区、文化体验。
7. 尽量考虑必去景点的地理分布。
8. 不要编造具体地址、坐标、开放时间或票价。
9. 这些只是待核实的关键词，不代表地点已核实。
10. 不要把预计旅行日期的开放情况说成已确认事实。

只返回合法 JSON，不要输出 Markdown。

JSON 格式：
{
  "candidates": [
    {
      "name": "候选地点名称",
      "reason": "推荐原因",
      "category": "景点或活动类型"
    }
  ]
}
"""

    payload = {
        "destination": requirements.get("destination"),
        "start_date": requirements.get("start_date"),
        "end_date": requirements.get("end_date"),
        "total_days": requirements.get("total_days"),
        "travelers": requirements.get("travelers"),
        "travel_style": requirements.get("travel_style"),
        "travel_pace": requirements.get("travel_pace"),
        "transport_preference": requirements.get(
            "transport_preference"
        ),
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

    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
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
                line
                for line in lines
                if not line.strip().startswith("```")
            ).strip()

        parsed = PlaceRecommendationResult.model_validate_json(
            content
        )

        blocked_names = {
            normalize_name(name)
            for name in (
                requirements.get("must_visit_places", [])
                + requirements.get("excluded_places", [])
            )
        }

        candidates = []
        seen = set()

        for item in parsed.candidates:
            name = item.name.strip()
            normalized = normalize_name(name)

            if (
                not normalized
                or normalized in blocked_names
                or normalized in seen
            ):
                continue

            seen.add(normalized)

            candidates.append({
                "name": name,
                "reason": item.reason,
                "category": item.category,
                "verified": False,
                "source": "llm_suggestion",
            })

        return {
            "candidate_keywords": candidates[:10],
            "status": "candidates_recommended",
            "error_message": None,
        }

    except Exception as exc:
        return {
            "candidate_keywords": [],
            "status": "failed",
            "error_message": (
                f"AI 推荐候选景点失败："
                f"{type(exc).__name__}: {exc}"
            ),
        }
