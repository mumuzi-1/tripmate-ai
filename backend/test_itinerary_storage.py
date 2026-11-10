
from app.core.database import SessionLocal

from app.services.itinerary_service import (
    save_trip_itinerary,
    get_trip_itinerary_versions,
    get_latest_trip_itinerary,
)


def main():
    trip_id = 1

    # 使用测试数据，避免重复调用大模型
    test_result = {
        "status": "route_checked",
        "validation_passed": True,
        "quality_passed": True,
        "quality_score": 100,
        "route_validation_passed": True,
        "route_warnings": [],
        "route_adjustments": [],
        "route_data": [
            {
                "origin_name": "灵隐寺",
                "destination_name": "西溪国家湿地公园",
                "transport_mode": "public_transport",
                "duration_min": 56.8,
                "source": "amap",
            }
        ],
        "itinerary": [
            {
                "day": 1,
                "date": "2027-04-03",
                "theme": "西湖城市观光",
                "activities": [
                    {
                        "start_time": "09:00",
                        "end_time": "13:00",
                        "place_name": "杭州西湖风景名胜区",
                        "description": "游览西湖",
                        "transport_suggestion": "公共交通",
                    },
                ],
            },
            {
                "day": 2,
                "date": "2027-04-04",
                "theme": "寺庙与自然风光",
                "activities": [
                    {
                        "start_time": "09:00",
                        "end_time": "12:00",
                        "place_name": "灵隐寺",
                        "description": "参观灵隐寺",
                        "transport_suggestion": "公共交通",
                    },
                    {
                        "start_time": "13:30",
                        "end_time": "17:30",
                        "place_name": "西溪国家湿地公园",
                        "description": "游览西溪湿地",
                        "transport_suggestion": "公共交通",
                    },
                ],
            },
            {
                "day": 3,
                "date": "2027-04-05",
                "theme": "老城区美食观光",
                "activities": [
                    {
                        "start_time": "09:00",
                        "end_time": "11:30",
                        "place_name": "南宋御街",
                        "description": "探索历史街区",
                        "transport_suggestion": "步行",
                    },
                    {
                        "start_time": "13:00",
                        "end_time": "15:30",
                        "place_name": "河坊街",
                        "description": "体验当地美食",
                        "transport_suggestion": "步行",
                    },
                ],
            },
        ],
    }

    print("=" * 50)
    print("TripMate AI - Itinerary Storage Test")
    print("=" * 50)

    with SessionLocal() as db:
        # 1. 保存测试行程
        record = save_trip_itinerary(
            db=db,
            trip_id=trip_id,
            result=test_result,
        )

        saved_id = record.id
        saved_version = record.version

        print("\n========== Save Result ==========")
        print("Saved ID:", saved_id)
        print("Trip ID:", record.trip_id)
        print("Version:", saved_version)
        print("Status:", record.status)
        print("Quality Score:", record.quality_score)

        # 2. 查询全部历史版本
        versions = get_trip_itinerary_versions(
            db=db,
            trip_id=trip_id,
        )

        print("\n========== Version History ==========")
        print("Total Versions:", len(versions))

        for item in versions:
            print(
                "Version:", item.version,
                "| ID:", item.id,
                "| Status:", item.status,
            )

        # 3. 查询最新版本
        latest = get_latest_trip_itinerary(
            db=db,
            trip_id=trip_id,
        )

        assert latest is not None
        assert latest.id == saved_id
        assert latest.version == saved_version
        assert len(latest.itinerary) == 3
        assert latest.quality_score == 100
        assert latest.route_validation_passed is True

        print("\n========== Latest Version ==========")
        print("Latest ID:", latest.id)
        print("Latest Version:", latest.version)
        print("Days:", len(latest.itinerary))
        print("Route Records:", len(latest.route_data))

    print("\nItinerary Storage Test OK")


if __name__ == "__main__":
    main()
