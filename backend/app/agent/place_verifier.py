
import os
import time

from dotenv import load_dotenv

from app.agent.candidate_filter import filter_candidates
from app.integrations.amap.client import AmapClient


class AmapRateLimitError(RuntimeError):
    """高德地图请求频率或配额受限。"""


def normalize_place_name(name: str, city: str) -> str:
    """统一景点名称，便于匹配。"""
    value = "".join(name.split()).lower()

    prefixes = [
        city + "市",
        city,
    ]

    for prefix in prefixes:
        if value.startswith(prefix.lower()):
            value = value[len(prefix):]
            break

    return value


def verify_candidate_places(
    city: str,
    keywords: list[str],
    verified_places: list[dict],
    excluded_names: list[str] | None = None,
    max_requests: int = 2,
) -> dict:
    """验证 AI 推荐地点，严格限制 API 请求数。"""

    load_dotenv()

    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        raise ValueError("未配置 AMAP_API_KEY")

    if not verified_places:
        raise ValueError("必须提供已核实的参考景点")

    client = AmapClient(api_key=api_key)

    all_candidates = []
    failed_keywords = []
    checked_count = 0
    seen_keywords = set()
    rate_limited = False

    for raw_keyword in keywords:
        keyword = raw_keyword.strip()

        normalized = normalize_place_name(
            keyword, city
        )

        if not normalized or normalized in seen_keywords:
            continue

        seen_keywords.add(normalized)

        if checked_count >= max_requests:
            break

        checked_count += 1
        print(f"Checking: {keyword}", flush=True)

        try:
            results = client.search_places(
                keywords=keyword,
                city=city,
            )

        except Exception as exc:
            message = str(exc)

            if (
                "CUQPS_HAS_EXCEEDED_THE_LIMIT" in message
                or "DAILY_QUERY_OVER_LIMIT" in message
                or "USER_DAILY_QUERY_OVER_LIMIT" in message
            ):
                print(
                    "Amap rate or quota limit detected. "
                    "Stopping further requests."
                )
                rate_limited = True
                failed_keywords.append(keyword)
                break

            print("Search error:", message)
            failed_keywords.append(keyword)
            continue

        exact_matches = []

        for place in results:
            name = place.get("name") or ""

            if (
                normalize_place_name(name, city)
                != normalized
            ):
                continue

            if not place.get("poi_id"):
                continue

            exact_matches.append(place)

        # 使用已核实的景点坐标进行地理筛选
        valid_places = filter_candidates(
            city=city,
            candidates=exact_matches,
            verified_places=verified_places,
            excluded_names=excluded_names or [],
            radius_km=40.0,
        )

        if not valid_places:
            print("No valid local match:", keyword)
            failed_keywords.append(keyword)
        else:
            # 只选距离参考区域最近的候选地点
            best = min(
                valid_places,
                key=lambda p: p["distance_from_center_km"],
            )

            all_candidates.append({
                **best,
                "requested_keyword": keyword,
                "verified": True,
                "source": "amap",
            })

            print(
                "Matched:",
                best["name"],
                "| Distance:",
                best["distance_from_center_km"],
                "km",
            )

        # 两次请求之间间隔，减小频率限制风险
        if checked_count < max_requests:
            time.sleep(2.0)

    return {
        "verified_places": all_candidates,
        "failed_keywords": failed_keywords,
        "requests_used": checked_count,
        "rate_limited": rate_limited,
    }
