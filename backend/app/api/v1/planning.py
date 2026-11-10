
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.graph import trip_graph
from app.core.auth import get_current_user
from app.core.database import get_db

from app.models.trip import Trip
from app.models.user import User
from app.models.trip_itinerary import TripItinerary

from app.services.itinerary_service import (
    save_trip_itinerary,
    get_trip_itinerary_versions,
)


router = APIRouter(
    prefix="/trips",
    tags=["AI 旅行规划"],
)


def verify_trip_owner(
    db: Session,
    trip_id: int,
    user_id: int,
) -> Trip:
    """验证旅行项目属于当前用户。"""

    trip = db.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.user_id == user_id,
        )
    )

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="旅行项目不存在或无权访问",
        )

    return trip


def serialize_itinerary(
    record: TripItinerary,
) -> dict:
    """将数据库行程记录转换为 API 返回格式。"""

    return {
        "itinerary_id": record.id,
        "trip_id": record.trip_id,
        "version": record.version,
        "status": record.status,
        "quality_score": record.quality_score,
        "validation_passed": record.validation_passed,
        "quality_passed": record.quality_passed,
        "route_validation_passed": (
            record.route_validation_passed
        ),
        "itinerary": record.itinerary,
        "route_data": record.route_data,
        "route_warnings": record.route_warnings,
        "route_adjustments": record.route_adjustments,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.post(
    "/{trip_id}/generate",
    summary="生成 AI 旅行行程并保存新版本",
)
def generate_trip_plan(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """运行 LangGraph 并保存 AI 行程。"""

    verify_trip_owner(
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    try:
        result = trip_graph.invoke({
            "trip_id": trip_id,
            "user_id": current_user.id,
            "retry_count": 0,
        })

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 旅行规划执行失败，请检查服务日志",
        )

    if (
        result.get("validation_passed") is not True
        or not result.get("itinerary")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI 未能生成通过基础校验的行程",
        )

    allowed_statuses = {
        "route_checked",
        "route_repaired",
        "route_needs_data",
        "route_not_applicable",
        "route_conflict",
    }

    if result.get("status") not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI 行程尚未达到可保存状态",
        )

    # 再次检查旅行项目归属
    db.expire_all()

    verify_trip_owner(
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    try:
        record = save_trip_itinerary(
            db=db,
            trip_id=trip_id,
            result=result,
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="行程已生成，但数据库保存失败",
        )

    return {
        "message": "AI 旅行行程已生成并保存",
        **serialize_itinerary(record),
    }


@router.get(
    "/{trip_id}/itineraries",
    summary="查询旅行项目的历史规划版本",
)
def list_trip_itineraries(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按版本号倒序查询历史行程。"""

    verify_trip_owner(
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    records = get_trip_itinerary_versions(
        db=db,
        trip_id=trip_id,
    )

    versions = []

    for record in records:
        versions.append({
            "itinerary_id": record.id,
            "trip_id": record.trip_id,
            "version": record.version,
            "status": record.status,
            "quality_score": record.quality_score,
            "validation_passed": record.validation_passed,
            "quality_passed": record.quality_passed,
            "route_validation_passed": (
                record.route_validation_passed
            ),
            "total_days": len(record.itinerary or []),
            "created_at": record.created_at.isoformat(),
        })

    return {
        "trip_id": trip_id,
        "total": len(versions),
        "latest_version": (
            versions[0]["version"]
            if versions
            else None
        ),
        "versions": versions,
    }


@router.get(
    "/{trip_id}/itineraries/{version}",
    summary="查询指定版本的完整旅行行程",
)
def get_trip_itinerary_detail(
    trip_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按版本号获取每日行程和交通路线。"""

    verify_trip_owner(
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    record = db.scalar(
        select(TripItinerary).where(
            TripItinerary.trip_id == trip_id,
            TripItinerary.version == version,
        )
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定版本的旅行行程不存在",
        )

    return serialize_itinerary(record)
