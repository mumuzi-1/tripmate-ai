
from datetime import date, datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class TripRequirementCreate(BaseModel):
    """创建或修改旅行需求"""

    departure_city: str = Field(
        min_length=1,
        max_length=100,
        description="出发城市",
    )

    start_date: date = Field(
        description="旅行开始日期",
    )

    end_date: date = Field(
        description="旅行结束日期",
    )

    travelers: int = Field(
        default=1,
        ge=1,
        le=100,
        description="旅行人数",
    )

    travel_style: str = Field(
        default="sightseeing",
        max_length=50,
        description="旅行类型",
    )

    travel_pace: str = Field(
        default="moderate",
        max_length=20,
        description="旅行节奏",
    )

    transport_preference: str = Field(
        default="public_transport",
        max_length=50,
        description="交通偏好",
    )

    accommodation_preference: str | None = Field(
        default=None,
        max_length=100,
        description="住宿偏好",
    )

    daily_start_time: time = Field(
        default=time(9, 0),
        description="每日开始游玩时间",
    )

    daily_end_time: time = Field(
        default=time(20, 0),
        description="每日结束游玩时间",
    )

    must_visit_places: list[str] = Field(
        default_factory=list,
        description="必去景点",
    )

    excluded_places: list[str] = Field(
        default_factory=list,
        description="不想去的景点",
    )

    preferred_activities: list[str] = Field(
        default_factory=list,
        description="偏好活动",
    )

    special_requirements: str | None = Field(
        default=None,
        max_length=5000,
        description="其他特殊要求",
    )

    @model_validator(mode="after")
    def validate_requirements(self):
        """检查日期和时间是否合法"""

        if self.end_date < self.start_date:
            raise ValueError(
                "旅行结束日期不能早于开始日期"
            )

        if self.daily_end_time <= self.daily_start_time:
            raise ValueError(
                "每日结束时间必须晚于开始时间"
            )

        overlap = set(self.must_visit_places) & set(
            self.excluded_places
        )

        if overlap:
            raise ValueError(
                "必去景点和排除景点不能重复"
            )

        return self


class TripRequirementResponse(TripRequirementCreate):
    """旅行需求响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    created_at: datetime
    updated_at: datetime
