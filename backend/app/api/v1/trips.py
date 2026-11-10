
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripResponse


router = APIRouter(
    prefix="/trips",
    tags=["旅行项目"],
)


# 1. 创建旅行
@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建旅行项目",
)
def create_trip(
    trip_data: TripCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = Trip(
        user_id=current_user.id,
        title=trip_data.title,
        destination=trip_data.destination,
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip


# 2. 查询当前用户的旅行列表
@router.get(
    "",
    response_model=list[TripResponse],
    summary="查询我的旅行列表",
)
def get_my_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
    )

    trips = db.scalars(statement).all()

    return trips


# 3. 查询旅行详情
@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    summary="查询旅行详情",
)
def get_trip_detail(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Trip).where(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    )

    trip = db.scalar(statement)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="旅行项目不存在或无权访问",
        )

    return trip
