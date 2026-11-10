
from app.agent.place_verifier import verify_candidate_places


def main():
    # 前面高德地图实际返回的三个参考地点
    verified_places = [
        {
            "name": "杭州西湖风景名胜区",
            "poi_id": "B023B13L9M",
            "longitude": 120.121358,
            "latitude": 30.222692,
        },
        {
            "name": "灵隐寺",
            "poi_id": "B023B02842",
            "longitude": 120.101406,
            "latitude": 30.240826,
        },
        {
            "name": "西溪国家湿地公园",
            "poi_id": "B023B06P06",
            "longitude": 120.061159,
            "latitude": 30.255079,
        },
    ]

    # 从本次 AI 推荐结果中选两个地点测试
    keywords = [
        "\u6cb3\u574a\u8857",
        "\u5357\u5b8b\u5fa1\u8857",
    ]

    result = verify_candidate_places(
        city="\u676d\u5dde",
        keywords=keywords,
        verified_places=verified_places,
        excluded_names=[],
        max_requests=2,
    )

    print("\n========== Verification Results ==========")
    print("Requests:", result["requests_used"])
    print("Valid Places:", len(result["verified_places"]))
    print("Rate Limited:", result["rate_limited"])
    print("Failed:", result["failed_keywords"])

    for place in result["verified_places"]:
        print("\nName:", place["name"])
        print("POI:", place["poi_id"])
        print("Longitude:", place["longitude"])
        print("Latitude:", place["latitude"])
        print(
            "Distance:",
            place["distance_from_center_km"],
            "km",
        )
        print("Verified:", place["verified"])

    if result["rate_limited"]:
        print("\nAmap Limit Detected")
    elif len(result["verified_places"]) == 2:
        print("\nPlace Verification OK")
    else:
        print("\nPlace Verification Incomplete")

    print("\nTest Finished")


if __name__ == "__main__":
    main()
