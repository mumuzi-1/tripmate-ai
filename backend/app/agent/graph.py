
from langgraph.graph import START, END, StateGraph

from app.agent.state import TripPlanState

from app.agent.nodes import (
    load_requirements,
    parse_requirements,
    search_places,
)

from app.agent.enrichment import enrich_places
from app.agent.itinerary import generate_itinerary
from app.agent.quality import check_itinerary_quality
from app.agent.repair import repair_itinerary, MAX_RETRIES
from app.agent.route_node import check_routes_node
from app.agent.route_repair import repair_route_times


def route_after_loading(state: TripPlanState) -> str:
    return (
        "success"
        if state.get("status") == "requirements_loaded"
        else "failed"
    )


def route_after_parsing(state: TripPlanState) -> str:
    return (
        "success"
        if state.get("status") == "requirements_parsed"
        else "failed"
    )


def route_after_search(state: TripPlanState) -> str:
    return (
        "success"
        if state.get("status") == "places_loaded"
        else "failed"
    )


def route_after_generation(state: TripPlanState) -> str:
    if (
        state.get("status") == "itinerary_generated"
        and state.get("validation_passed") is True
    ):
        return "success"

    return "failed"


def quality_check_node(state: TripPlanState) -> dict:
    """执行行程质量检查。"""

    result = check_itinerary_quality(state)

    return {
        **result,
        "status": (
            "quality_checked"
            if result["quality_passed"]
            else "quality_needs_improvement"
        ),
    }


def route_after_quality(state: TripPlanState) -> str:
    """质量通过则检查交通，否则尝试 AI 修正。"""

    if state.get("quality_passed") is True:
        return "check_routes"

    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "finished"

    return "repair"


def route_after_repair(state: TripPlanState) -> str:
    """决定 AI 行程修正后如何继续。"""

    if state.get("quality_passed") is True:
        return "check_routes"

    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "finished"

    if state.get("status") == "failed":
        return "finished"

    return "retry"


def route_after_route_check(state: TripPlanState) -> str:
    """交通时间冲突时进入自动修正。"""

    if state.get("status") == "route_conflict":
        return "repair_route"

    # 路线已通过、缺数据或无须检查时均结束
    # 缺数据不代表通过，最终状态会保留警告
    return "finished"


def build_trip_graph():
    """构建 TripMate AI 完整工作流。"""

    builder = StateGraph(TripPlanState)

    # 注册业务节点
    builder.add_node(
        "load_requirements",
        load_requirements,
    )

    builder.add_node(
        "parse_requirements",
        parse_requirements,
    )

    builder.add_node(
        "search_places",
        search_places,
    )

    builder.add_node(
        "enrich_places",
        enrich_places,
    )

    builder.add_node(
        "generate_itinerary",
        generate_itinerary,
    )

    builder.add_node(
        "check_quality",
        quality_check_node,
    )

    builder.add_node(
        "repair_itinerary",
        repair_itinerary,
    )

    builder.add_node(
        "check_routes",
        check_routes_node,
    )

    # 新增：交通时间自动修正
    builder.add_node(
        "repair_route_times",
        repair_route_times,
    )

    # 工作流入口
    builder.add_edge(
        START,
        "load_requirements",
    )

    builder.add_conditional_edges(
        "load_requirements",
        route_after_loading,
        {
            "success": "parse_requirements",
            "failed": END,
        },
    )

    builder.add_conditional_edges(
        "parse_requirements",
        route_after_parsing,
        {
            "success": "search_places",
            "failed": END,
        },
    )

    builder.add_conditional_edges(
        "search_places",
        route_after_search,
        {
            "success": "enrich_places",
            "failed": END,
        },
    )

    # 景点拓展失败不影响必去景点规划
    builder.add_edge(
        "enrich_places",
        "generate_itinerary",
    )

    builder.add_conditional_edges(
        "generate_itinerary",
        route_after_generation,
        {
            "success": "check_quality",
            "failed": END,
        },
    )

    builder.add_conditional_edges(
        "check_quality",
        route_after_quality,
        {
            "check_routes": "check_routes",
            "repair": "repair_itinerary",
            "finished": END,
        },
    )

    builder.add_conditional_edges(
        "repair_itinerary",
        route_after_repair,
        {
            "check_routes": "check_routes",
            "retry": "repair_itinerary",
            "finished": END,
        },
    )

    # 新增：发现交通时间冲突后自动修正
    builder.add_conditional_edges(
        "check_routes",
        route_after_route_check,
        {
            "repair_route": "repair_route_times",
            "finished": END,
        },
    )

    # repair_route_times 内部已经重新执行交通校验
    builder.add_edge(
        "repair_route_times",
        END,
    )

    return builder.compile()


trip_graph = build_trip_graph()
