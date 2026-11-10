
from typing import Any, TypedDict


class TripPlanState(TypedDict, total=False):
    """TripMate AI 旅行规划工作流状态"""

    trip_id: int
    user_id: int

    # 旅行需求
    requirements: dict[str, Any]
    parsed_requirements: dict[str, Any]

    # 景点数据
    places: list[dict[str, Any]]
    candidate_keywords: list[dict[str, Any]]
    additional_places: list[dict[str, Any]]
    all_places: list[dict[str, Any]]
    place_verification_info: dict[str, Any]

    # AI 行程
    itinerary: list[dict[str, Any]]

    # 基础校验
    validation_passed: bool
    validation_errors: list[str]

    # 行程质量检查
    quality_passed: bool
    quality_warnings: list[str]
    quality_score: int

    # 交通路线与校验
    route_data: list[dict[str, Any]]
    route_validation_passed: bool | None
    route_warnings: list[str]
    route_checks: list[dict[str, Any]]
    route_requests_used: int

    # 交通时间自动修正记录
    route_adjustments: list[dict[str, Any]]

    # AI 重试次数
    retry_count: int

    # 工作流状态
    status: str
    error_message: str | None
