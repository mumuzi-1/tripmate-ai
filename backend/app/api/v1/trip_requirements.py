
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.trip import Trip
from app.models import TripRequirement
from app.schemas.trip_requirement import (
    TripRequirementCreate,
    TripRequirementResponse,
)


router = APIRouter(
    prefix="/trips",
    tags=["旅行需求"],
)


# 统一检查旅行项目是否属于当前登录用户
def check_trip_owner(
    trip_id: int,
    db: Session,
    current_user: User,
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


# 1. 创建旅行需求
@router.post(
    "/{trip_id}/requirements",
    response_model=TripRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建旅行需求",
)
def create_trip_requirement(
    trip_id: int,
    requirement_data: TripRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_trip_owner(trip_id, db, current_user)

    existing = db.scalar(
        select(TripRequirement).where(
            TripRequirement.trip_id == trip_id
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该旅行项目已经存在需求，请使用修改接口",
        )

    requirement = TripRequirement(
        trip_id=trip_id,
        **requirement_data.model_dump(),
    )

    db.add(requirement)
    db.commit()
    db.refresh(requirement)

    return requirement


# 2. 查询旅行需求
@router.get(
    "/{trip_id}/requirements",
    response_model=TripRequirementResponse,
    summary="查询旅行需求",
)
def get_trip_requirement(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_trip_owner(trip_id, db, current_user)

    requirement = db.scalar(
        select(TripRequirement).where(
            TripRequirement.trip_id == trip_id
        )
    )

    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该旅行项目尚未设置需求",
        )

    return requirement


# 3. 修改旅行需求
@router.put(
    "/{trip_id}/requirements",
    response_model=TripRequirementResponse,
    summary="修改旅行需求",
)
def update_trip_requirement(
    trip_id: int,
    requirement_data: TripRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_trip_owner(trip_id, db, current_user)

    requirement = db.scalar(
        select(TripRequirement).where(
            TripRequirement.trip_id == trip_id
        )
    )

    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该旅行项目尚未设置需求",
        )

    update_data = requirement_data.model_dump()

    for key, value in update_data.items():
        setattr(requirement, key, value)

    db.commit()
    db.refresh(requirement)

    return requirement


# 4. 删除旅行需求
@router.delete(
    "/{trip_id}/requirements",
    summary="删除旅行需求",
)
def delete_trip_requirement(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_trip_owner(trip_id, db, current_user)

    requirement = db.scalar(
        select(TripRequirement).where(
            TripRequirement.trip_id == trip_id
        )
    )

    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该旅行项目尚未设置需求",
        )

    db.delete(requirement)
    db.commit()

    return {
        "code": 200,
        "message": "旅行需求删除成功",
    }
