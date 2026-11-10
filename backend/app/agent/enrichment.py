
from app.agent.state import TripPlanState
from app.agent.place_recommender import recommend_places
from app.agent.place_verifier import verify_candidate_places


MAX_AMAP_REQUESTS = 2


def enrich_places(state: TripPlanState) -> dict:
    """推荐并核实可选景点，不改变原有必去景点。"""

    required_places = state.get("places", [])
    requirements = state.get("parsed_requirements", {})

    if not requirements or not required_places:
        return {
            "status": "places_partially_loaded",
            "candidate_keywords": [],
            "additional_places": [],
            "all_places": required_places,
            "error_message": "缺少旅行需求或必去景点",
        }

    # 第一步：Qwen 推荐候选关键词
    recommendation = recommend_places(state)

    if recommendation.get("status") != "candidates_recommended":
        return {
            "status": "places_partially_loaded",
            "candidate_keywords": [],
            "additional_places": [],
            "all_places": required_places,
            "place_verification_info": {
                "requests_used": 0,
                "rate_limited": False,
                "failed_keywords": [],
                "warning": recommendation.get("error_message"),
            },
        }

    suggestions = recommendation.get(
        "candidate_keywords", []
    )

    keywords = [
        item["name"]
        for item in suggestions
    ]

    # 第二步：高德核验推荐地点
    try:
        verification = verify_candidate_places(
            city=requirements["destination"],
            keywords=keywords,
            verified_places=required_places,
            excluded_names=requirements.get(
                "excluded_places", []
            ),
            max_requests=MAX_AMAP_REQUESTS,
        )

    except Exception as exc:
        return {
            "status": "places_partially_loaded",
            "candidate_keywords": suggestions,
            "additional_places": [],
            "all_places": required_places,
            "place_verification_info": {
                "requests_used": 0,
                "rate_limited": False,
                "failed_keywords": [],
                "warning": str(exc),
            },
        }

    additional_places = verification.get(
        "verified_places", []
    )

    # 保留必去景点，补充景点单独保存
    all_places = required_places + additional_places

    return {
        "candidate_keywords": suggestions,
        "additional_places": additional_places,
        "all_places": all_places,
        "place_verification_info": {
            "requests_used": verification["requests_used"],
            "rate_limited": verification["rate_limited"],
            "failed_keywords": verification["failed_keywords"],
        },
        "status": (
            "places_enriched"
            if additional_places
            else "places_partially_loaded"
        ),
        "error_message": None,
    }
