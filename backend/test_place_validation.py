
from app.agent.place_discovery import select_valid_place


CITY = "\u676d\u5dde"
KEYWORD = "\u96f7\u5cf0\u5854"


def make_place(
    poi_id: str,
    longitude: float,
    latitude: float,
) -> dict:
    return {
        "name": KEYWORD,
        "poi_id": poi_id,
        "longitude": longitude,
        "latitude": latitude,
        "address": "",
    }


def main():
    wrong_place = make_place(
        "wrong_test",
        111.553129,
        32.823021,
    )

    local_place = make_place(
        "local_test",
        120.149,
        30.231,
    )

    # 测试1：异地地点排除
    result1 = select_valid_place(
        candidates=[wrong_place],
        keyword=KEYWORD,
        city=CITY,
    )

    assert result1 is None
    print("Test 1: Wrong City Rejected - OK")

    # 测试2：同名时选择杭州本地地点
    result2 = select_valid_place(
        candidates=[wrong_place, local_place],
        keyword=KEYWORD,
        city=CITY,
    )

    assert result2 == local_place
    print("Test 2: Local Place Selected - OK")

    # 测试3：没有候选地点
    result3 = select_valid_place(
        candidates=[],
        keyword=KEYWORD,
        city=CITY,
    )

    assert result3 is None
    print("Test 3: Empty Candidates - OK")

    # 测试4：正确地点可以被识别
    result4 = select_valid_place(
        candidates=[local_place],
        keyword=KEYWORD,
        city=CITY,
    )

    assert result4 == local_place
    print("Test 4: Valid Place Accepted - OK")

    print("\nAll Place Validation Tests Passed")


if __name__ == "__main__":
    main()
