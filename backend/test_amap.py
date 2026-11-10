
import os

from dotenv import load_dotenv

from app.integrations.amap.client import AmapClient


def main():
    # 读取 backend/.env
    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        print("错误：未找到 AMAP_API_KEY")
        print("请先完成上一步的高德地图 Key 配置。")
        return

    client = AmapClient(api_key=api_key)

    attractions = [
        "西湖风景名胜区",
        "灵隐寺",
        "西溪国家湿地公园",
    ]

    print("=" * 50)
    print("TripMate AI - 高德地图景点搜索测试")
    print("=" * 50)

    success_count = 0

    for attraction in attractions:
        print(f"\n正在搜索：{attraction}")

        try:
            places = client.search_places(
                keywords=attraction,
                city="杭州",
            )

            if not places:
                print("搜索结果为空")
                continue

            # 显示候选结果，后续再做精确匹配
            for index, place in enumerate(places[:3], start=1):
                print(f"\n候选地点 {index}")
                print("名称：", place.get("name"))
                print("地址：", place.get("address"))
                print("经度：", place.get("longitude"))
                print("纬度：", place.get("latitude"))
                print("POI ID：", place.get("poi_id"))

            success_count += 1

        except Exception as exc:
            print(
                f"搜索失败：{type(exc).__name__}: {exc}"
            )

    print("\n" + "=" * 50)
    print(f"成功返回候选地点的搜索数：{success_count}/3")

    if success_count == 3:
        print("Amap API Search OK")
    else:
        print("部分搜索失败，请检查 API Key 或接口响应")

    print("=" * 50)


if __name__ == "__main__":
    main()
