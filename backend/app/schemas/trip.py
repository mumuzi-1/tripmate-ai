
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TripCreate(BaseModel):
    """创建旅行请求"""

    title: str = Field(
        min_length=1,
        max_length=100,
        description="旅行名称",
    )

    destination: str = Field(
        min_length=1,
        max_length=100,
        description="旅行目的地",
    )


class TripResponse(BaseModel):
    """旅行信息响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    destination: str
    status: str
    created_at: datetime
    updated_at: datetime
