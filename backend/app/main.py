
from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.trips import router as trips_router
from app.api.v1.trip_requirements import router as trip_requirements_router
from app.api.v1.planning import router as planning_router
app = FastAPI(
    title="TripMate AI",
    description="智能旅行规划与路线可视化平台",
    version="0.1.0",
)

# 用户认证路由
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["用户认证"],
)

# 旅行项目路由
app.include_router(
    trips_router,
    prefix="/api/v1",
)

# AI 行程生成与保存
app.include_router(
    planning_router,
    prefix="/api/v1",
)

# 旅行需求路由
app.include_router(
    trip_requirements_router,
    prefix="/api/v1",
)
@app.get("/")
def root():
    return {
        "message": "Welcome to TripMate AI",
        "status": "running",
    }


@app.get("/api/v1/health")
def health_check():
    return {
        "code": 200,
        "message": "TripMate AI backend is running",
        "data": {
            "status": "ok",
        },
    }

# TripMate AI - Saved Map Data API
from app.api.v1.map_data import router as map_data_router
app.include_router(map_data_router)


# TripMate AI - Amap JS API Proxy
from app.integrations.amap.js_proxy import router as amap_js_router

app.include_router(amap_js_router)
