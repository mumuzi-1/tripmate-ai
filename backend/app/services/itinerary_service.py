
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.models.trip_itinerary import TripItinerary


def save_trip_itinerary(
    db: Session,
    trip_id: int,
    result: dict[str, Any],
) -> TripItinerary:
    """保存 AI 旅行规划结果，每次保存创建一个新版本。"""

    if not result.get("itinerary"):
        raise ValueError("行程为空，不能保存")

    status = result.get("status", "")

    allowed_statuses = {
        "route_checked",
        "route_repaired",
        "route_needs_data",
        "route_not_applicable",
        "route_conflict",
    }

    if status not in allowed_statuses:
        raise ValueError(
            f"当前规划状态不允许保存：{status}"
        )

    if result.get("validation_passed") is not True:
        raise ValueError("基础行程校验未通过，不能保存")

    try:
        # 锁定旅行项目，避免并发保存时生成重复版本号
        trip = db.scalar(
            select(Trip)
            .where(Trip.id == trip_id)
            .with_for_update()
        )

        if trip is None:
            raise ValueError(
                f"旅行项目不存在：{trip_id}"
            )

        # 查询该旅行项目已有的最大版本号
        latest_version = db.scalar(
            select(
                func.max(TripItinerary.version)
            ).where(
                TripItinerary.trip_id == trip_id
            )
        )

        next_version = (
            (latest_version or 0) + 1
        )

        # 构建行程记录
        record = TripItinerary(
            trip_id=trip_id,
            version=next_version,
            status=status,
            itinerary=result["itinerary"],
            route_data=result.get("route_data", []),
            quality_score=result.get("quality_score"),
            validation_passed=result.get(
                "validation_passed"
            ),
            quality_passed=result.get(
                "quality_passed"
            ),
            route_validation_passed=result.get(
                "route_validation_passed"
            ),
            route_warnings=result.get(
                "route_warnings", []
            ),
            route_adjustments=result.get(
                "route_adjustments", []
            ),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    except Exception:
        db.rollback()
        raise


def get_trip_itinerary_versions(
    db: Session,
    trip_id: int,
) -> list[TripItinerary]:
    """查询指定旅行项目的全部规划版本。"""

    statement = (
        select(TripItinerary)
        .where(TripItinerary.trip_id == trip_id)
        .order_by(TripItinerary.version.desc())
    )

    return list(db.scalars(statement).all())


def get_latest_trip_itinerary(
    db: Session,
    trip_id: int,
) -> TripItinerary | None:
    """查询指定旅行项目的最新规划版本。"""

    statement = (
        select(TripItinerary)
        .where(TripItinerary.trip_id == trip_id)
        .order_by(TripItinerary.version.desc())
        .limit(1)
    )

    return db.scalar(statement)
