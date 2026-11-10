
from app.agent.state import TripPlanState
from app.agent.nodes import (
    load_requirements,
    parse_requirements,
    search_places,
)
from app.agent.place_recommender import recommend_places
from app.agent.place_verifier import verify_candidate_places


def build_place_pipeline(
    trip_id: int,
    user_id: int,
    max_requests: int = 2,
) -> dict:
    """读取旅行需求、推荐候选景点并核验 POI。"""

    state: TripPlanState = {
        "trip_id": trip_id,
        "user_id": user_id,
        "retry_count": 0,
    }

    # 1. 读取 MySQL 旅行需求
    state.update(load_requirements(state))

    if state.get("status") != "requirements_loaded":
        return {
            "status": "failed",
            "error_message": state.get("error_message"),
        }

    # 2. 解析旅行约束
    state.update(parse_requirements(state))

    if state.get("status") != "requirements_parsed":
        return {
            "status": "failed",
            "error_message": state.get("error_message"),
        }

    # 3. 搜索用户指定的必去景点
    state.update(search_places(state))

    if state.get("status") != "places_loaded":
        return {
            "status": "failed",
            "error_message": state.get("error_message"),
        }

    required_places = state.get("places", [])
    requirements = state["parsed_requirements"]
    city = requirements["destination"]

    # 4. 让 Qwen 推荐额外景点关键词
    recommendation = recommend_places(state)

    if recommendation.get("status") != "candidates_recommended":
        return {
            "status": "failed",
            "error_message": recommendation.get("error_message"),
            "required_places": required_places,
        }

    suggestions = recommendation.get(
        "candidate_keywords", []
    )

    keywords = [
        item["name"]
        for item in suggestions
    ]

    # 5. 调用高德地图核验候选地点
    try:
        verification = verify_candidate_places(
            city=city,
            keywords=keywords,
            verified_places=required_places,
            excluded_names=requirements.get(
                "excluded_places", []
            ),
            max_requests=max_requests,
        )
    except Exception as exc:
        return {
            "status": "verification_failed",
            "error_message": str(exc),
            "required_places": required_places,
            "suggested_places": suggestions,
        }

    additional_places = verification["verified_places"]

    # 6. 合并必去景点与已核验候选景点
    all_places = required_places + additional_places

    return {
        "status": (
            "places_enriched"
            if additional_places
            else "places_partially_loaded"
        ),
        "trip_id": trip_id,
        "destination": city,
        "required_places": required_places,
        "suggested_places": suggestions,
        "additional_places": additional_places,
        "all_places": all_places,
        "requests_used": verification["requests_used"],
        "rate_limited": verification["rate_limited"],
        "failed_keywords": verification["failed_keywords"],
        "error_message": None,
    }
