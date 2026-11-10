from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.trip import Trip
from app.models.trip_itinerary import TripItinerary
from app.models.user import User


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["Trip Map"],
)


@router.get("/{trip_id}/map-data")
def get_trip_map_data(
    trip_id: int,
    version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify trip ownership before reading itinerary data.
    trip = db.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    query = select(TripItinerary).where(
        TripItinerary.trip_id == trip_id,
    )

    if version is not None:
        query = query.where(
            TripItinerary.version == version
        )
    else:
        query = query.order_by(
            TripItinerary.version.desc()
        )

    record = db.scalar(query)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Saved itinerary not found",
        )

    days = record.itinerary or []
    saved_routes = record.route_data or []

    if isinstance(saved_routes, dict):
        saved_routes = saved_routes.get("routes", [])

    if not isinstance(saved_routes, list):
        saved_routes = []

    places = []

    for day in days:
        for index, activity in enumerate(
            day.get("activities", [])
        ):
            places.append({
                "day": day.get("day"),
                "date": day.get("date"),
                "sequence": index + 1,
                "name": activity.get("place_name"),
                "start_time": activity.get("start_time"),
                "end_time": activity.get("end_time"),
                "longitude": activity.get("longitude"),
                "latitude": activity.get("latitude"),
                "poi_id": activity.get("poi_id"),
            })

    routes = []

    for index, item in enumerate(saved_routes):
        if not isinstance(item, dict):
            continue

        details = item.get("details") or {}

        if not isinstance(details, dict):
            details = {}

        routes.append({
            "index": index + 1,
            "origin_name": item.get("origin_name"),
            "destination_name": item.get(
                "destination_name"
            ),
            "transport_mode": item.get(
                "transport_mode"
            ),
            "duration_min": item.get("duration_min"),
            "source": item.get("source"),
            "distance_m": details.get("distance_m"),
            "walking_distance_m": details.get(
                "walking_distance_m"
            ),
            "details": details,
        })


    # MAP_COORDINATE_CACHE_V1
    # Enrich the response only; do not modify stored itinerary versions.
    import json
    import math
    from pathlib import Path

    cache_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "poi_cache.json"
    )

    if cache_path.is_file():
        try:
            cache = json.loads(
                cache_path.read_text(encoding="utf-8-sig")
            )

            trip_city = str(trip.destination or "").strip()
            cache_city = str(cache.get("city") or "").strip()

            if trip_city.rstrip("\u5e02") == cache_city.rstrip("\u5e02"):
                cached_places = cache.get("places", {})

                if isinstance(cached_places, dict):
                    for place in places:
                        item = cached_places.get(place["name"])

                        if not isinstance(item, dict):
                            continue

                        try:
                            lon = float(item["longitude"])
                            lat = float(item["latitude"])

                            if not (
                                item.get("verified") is True
                                and item.get("poi_id")
                                and math.isfinite(lon)
                                and math.isfinite(lat)
                                and 119 < lon < 121
                                and 29 < lat < 31
                            ):
                                continue
                        except (ValueError, TypeError, KeyError):
                            continue

                        if (
                            place["longitude"] is None
                            or place["latitude"] is None
                        ):
                            place["longitude"] = lon
                            place["latitude"] = lat
                            place["poi_id"] = item["poi_id"]

        except (OSError, ValueError, TypeError):
            pass


    # TRIPMATE_WALKING_OVERLAY_V1
    # Enrich API response only; do not change database records.
    import json as _route_json
    import math as _route_math
    from pathlib import Path as _RoutePath

    _route_cache_path = (
        _RoutePath(__file__).resolve().parents[3]
        / "data"
        / "route_geometry_cache.json"
    )

    if _route_cache_path.is_file():
        try:
            _route_cache = _route_json.loads(
                _route_cache_path.read_text(encoding="utf-8-sig")
            )
            _cached_routes = _route_cache.get("routes", {})

            if isinstance(_cached_routes, dict):
                for _route in routes:
                    for _cached in _cached_routes.values():
                        if not isinstance(_cached, dict):
                            continue

                        if (
                            _cached.get("trip_id") != trip.id
                            or _cached.get("version") != record.version
                            or _cached.get("origin_name")
                                != _route.get("origin_name")
                            or _cached.get("destination_name")
                                != _route.get("destination_name")
                            or _cached.get("transport_mode")
                                != _route.get("transport_mode")
                            or _cached.get("source") != "amap"
                        ):
                            continue

                        _points = _cached.get("polyline")

                        if (
                            not isinstance(_points, list)
                            or not 2 <= len(_points) <= 10000
                        ):
                            continue

                        _valid = True

                        for _point in _points:
                            if (
                                not isinstance(_point, (list, tuple))
                                or len(_point) != 2
                            ):
                                _valid = False
                                break

                            try:
                                _lon = float(_point[0])
                                _lat = float(_point[1])
                            except (TypeError, ValueError):
                                _valid = False
                                break

                            if not (
                                _route_math.isfinite(_lon)
                                and _route_math.isfinite(_lat)
                                and 119 < _lon < 121
                                and 29 < _lat < 31
                            ):
                                _valid = False
                                break

                        if _valid:
                            _route["polyline"] = _points
                            _route["geometry_source"] = "amap_cache"
                            _route["geometry_distance_m"] = (
                                _cached.get("distance_m")
                            )
                            _route["geometry_duration_min"] = (
                                _cached.get("duration_min")
                            )
                            break

        except (OSError, ValueError, TypeError, AttributeError):
            pass

    has_coordinates = all(
        item["longitude"] is not None
        and item["latitude"] is not None
        for item in places
    ) if places else False

    # TRIPMATE_TRANSIT_MAP_BRIDGE_V1
    # Include cached alternative geometry in existing JWT-protected map data.
    _transit_alternative = None

    try:
        import json as _json
        import math as _math
        from pathlib import Path as _Path

        _cache_file = (
            _Path(__file__).resolve().parents[3]
            / "data"
            / "route_geometry_cache.json"
        )

        if _cache_file.is_file():
            _cache_data = _json.loads(
                _cache_file.read_text(encoding="utf-8-sig")
            )
            _entries = _cache_data.get("routes", {})
            _entry = _entries.get(
                "trip4_v1_lingyin_to_xixi_transit"
            ) if isinstance(_entries, dict) else None

            if (
                isinstance(_entry, dict)
                and _entry.get("trip_id") == trip.id
                and _entry.get("version") == record.version
                and _entry.get("source") == "amap"
                and _entry.get("transport_mode") == "public_transport"
            ):
                _origin = _entry.get("origin_name")
                _destination = _entry.get("destination_name")

                _saved = next(
                    (
                        item for item in routes
                        if item.get("origin_name") == _origin
                        and item.get("destination_name") == _destination
                        and item.get("transport_mode") == "public_transport"
                    ),
                    None,
                )

                if _saved is not None:
                    _segments = []
                    _raw_segments = _entry.get("segments", [])

                    if isinstance(_raw_segments, list) and len(_raw_segments) <= 500:
                        for _part in _raw_segments:
                            if not isinstance(_part, dict):
                                continue
                            if _part.get("mode") not in (
                                "walking", "bus", "subway"
                            ):
                                continue

                            _raw_points = _part.get("polyline")
                            if not isinstance(_raw_points, list):
                                continue
                            if not 2 <= len(_raw_points) <= 10000:
                                continue

                            _points = []
                            for _point in _raw_points:
                                if not isinstance(_point, (list, tuple)):
                                    break
                                if len(_point) != 2:
                                    break
                                try:
                                    _lon = float(_point[0])
                                    _lat = float(_point[1])
                                except (ValueError, TypeError):
                                    break
                                if not (
                                    _math.isfinite(_lon)
                                    and _math.isfinite(_lat)
                                    and 119 < _lon < 121
                                    and 29 < _lat < 31
                                ):
                                    break
                                _points.append([_lon, _lat])

                            if len(_points) != len(_raw_points):
                                continue

                            _segments.append({
                                "mode": _part["mode"],
                                "name": str(_part.get("name") or ""),
                                "polyline": _points,
                            })

                    if _segments:
                        _transit_alternative = {
                            "route_type": "alternative",
                            "matches_original": bool(
                                _entry.get("matches_saved_lines") is True
                            ),
                            "origin_name": _origin,
                            "destination_name": _destination,
                            "saved_duration_min": _saved.get("duration_min"),
                            "alternative_duration_min": _entry.get("duration_min"),
                            "line_names": _entry.get("line_names") or [],
                            "segments": _segments,
                            "source": "amap_cache",
                        }

    except (OSError, ValueError, TypeError, AttributeError):
        # Optional map overlay must not break the main itinerary API.
        _transit_alternative = None


    return {
        "trip_id": trip.id,
        "trip_title": trip.title,
        "destination": trip.destination,
        "version": record.version,
        "status": record.status,
        "coordinate_complete": has_coordinates,
        "places": places,
        "routes": routes,
        "transit_alternative": _transit_alternative,
        "total_places": len(places),
        "total_routes": len(routes),
        "route_validation_passed":
            record.route_validation_passed,
        "route_warnings": record.route_warnings or [],
    }
from fastapi import HTTPException as POIHTTPException
from app.agent.place_verifier import verify_candidate_places


@router.post("/{trip_id}/map-pois")
def resolve_trip_map_pois(
    trip_id: int,
    version: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import math
    import os

    from app.integrations.amap.client import AmapClient
    from app.agent.place_discovery import select_valid_place, normalize_name

    # Authentication and ownership are enforced by this query.
    map_data = get_trip_map_data(
        trip_id=trip_id,
        version=version,
        db=db,
        current_user=current_user,
    )

    city = str(map_data["destination"] or "").strip()

    # Existing place filter is currently Hangzhou-specific.
    if city not in ("\u676d\u5dde", "\u676d\u5dde\u5e02"):
        raise HTTPException(
            status_code=422,
            detail="POI verification currently supports Hangzhou only",
        )

    names = list(dict.fromkeys(
        place["name"].strip()
        for place in map_data["places"]
        if isinstance(place.get("name"), str)
        and place["name"].strip()
    ))

    batch = names[offset:offset + 2]

    response = {
        "trip_id": trip_id,
        "version": map_data["version"],
        "offset": offset,
        "next_offset": (
            offset + len(batch)
            if offset + len(batch) < len(names)
            else None
        ),
        "total_unique_places": len(names),
        "verified_places": [],
        "failed_keywords": [],
        "requests_used": 0,
        "rate_limited": False,
    }

    if not batch:
        return response


    # POI_CACHE_LOOKUP_V1
    # Fully cached batches return without any Amap API request.
    import json
    import math
    from pathlib import Path

    cache_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "poi_cache.json"
    )

    cached_places = {}

    if cache_path.is_file():
        try:
            cache_data = json.loads(
                cache_path.read_text(encoding="utf-8-sig")
            )

            if cache_data.get("city") in (
                "\u676d\u5dde",
                "\u676d\u5dde\u5e02",
            ):
                cached_places = cache_data.get("places", {})
        except (OSError, ValueError, TypeError):
            cached_places = {}

    cache_hits = []

    for keyword in batch:
        item = cached_places.get(keyword)

        if not isinstance(item, dict):
            break

        try:
            lon = float(item["longitude"])
            lat = float(item["latitude"])

            if not (
                item.get("verified") is True
                and item.get("poi_id")
                and math.isfinite(lon)
                and math.isfinite(lat)
                and 119 < lon < 121
                and 29 < lat < 31
            ):
                break
        except (KeyError, ValueError, TypeError):
            break

        cache_hits.append({
            "requested_keyword": keyword,
            "name": item.get("name", keyword),
            "longitude": lon,
            "latitude": lat,
            "poi_id": item["poi_id"],
            "verified": True,
            "source": "amap_cache",
        })

    if len(cache_hits) == len(batch):
        response["verified_places"] = cache_hits
        response["requests_used"] = 0
        return response


    api_key = os.getenv("AMAP_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AMAP_API_KEY is not configured",
        )

    client = AmapClient(api_key=api_key)

    for keyword in batch:
        try:
            candidates = client.search_places(
                keywords=keyword,
                city=city,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Amap POI search failed",
            ) from exc

        response["requests_used"] += 1

        if not isinstance(candidates, list):
            response["failed_keywords"].append(keyword)
            continue

        try:
            place = select_valid_place(
                candidates=candidates,
                keyword=normalize_name(keyword, city),
                city=city,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="POI candidate validation failed",
            ) from exc

        if not place:
            response["failed_keywords"].append(keyword)
            continue

        try:
            lon = float(place["longitude"])
            lat = float(place["latitude"])

            if not (
                math.isfinite(lon)
                and math.isfinite(lat)
                and -180 <= lon <= 180
                and -90 <= lat <= 90
            ):
                raise ValueError("Invalid coordinates")
        except (ValueError, TypeError, KeyError):
            response["failed_keywords"].append(keyword)
            continue

        response["verified_places"].append({
            "requested_keyword": keyword,
            "name": place.get("name"),
            "longitude": lon,
            "latitude": lat,
            "poi_id": place.get("poi_id"),
            "verified": True,
            "source": "amap",
        })

    return response



# TRIPMATE_ROUTE_GEOMETRY_API_V1
@router.get("/{trip_id}/route-geometry")
def get_trip_route_geometry(
    trip_id: int,
    version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json
    import math
    from pathlib import Path

    # Reuse the existing trip ownership and version checks.
    map_data = get_trip_map_data(
        trip_id=trip_id,
        version=version,
        db=db,
        current_user=current_user,
    )

    resolved_version = map_data["version"]

    result = {
        "trip_id": trip_id,
        "version": resolved_version,
        "routes": [],
        "total_routes": 0,
        "source": "local_cache",
    }

    cache_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "route_geometry_cache.json"
    )

    if not cache_path.is_file():
        return result

    try:
        cache = json.loads(
            cache_path.read_text(encoding="utf-8-sig")
        )
    except (OSError, ValueError):
        raise HTTPException(
            status_code=500,
            detail="Route geometry cache is unreadable",
        )

    if not isinstance(cache, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid route cache structure",
        )

    entries = cache.get("routes", {})

    if not isinstance(entries, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid cached routes",
        )

    saved_pairs = {
        (
            item.get("origin_name"),
            item.get("destination_name"),
            item.get("transport_mode"),
        )
        for item in map_data.get("routes", [])
    }

    for item in entries.values():
        if not isinstance(item, dict):
            continue

        if (
            item.get("trip_id") != trip_id
            or item.get("version") != resolved_version
            or item.get("transport_mode") != "walking"
            or item.get("source") != "amap"
        ):
            continue

        pair = (
            item.get("origin_name"),
            item.get("destination_name"),
            item.get("transport_mode"),
        )

        if pair not in saved_pairs:
            continue

        raw = item.get("polyline")

        if not isinstance(raw, list) or len(raw) < 2:
            continue

        if len(raw) > 10000:
            continue

        points = []
        valid = True

        for point in raw:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                valid = False
                break

            try:
                lon = float(point[0])
                lat = float(point[1])
            except (ValueError, TypeError):
                valid = False
                break

            if not (
                math.isfinite(lon)
                and math.isfinite(lat)
                and 119 < lon < 121
                and 29 < lat < 31
            ):
                valid = False
                break

            points.append([lon, lat])

        if not valid:
            continue

        result["routes"].append({
            "origin_name": pair[0],
            "destination_name": pair[1],
            "transport_mode": "walking",
            "distance_m": item.get("distance_m"),
            "duration_min": item.get("duration_min"),
            "polyline": points,
            "point_count": len(points),
            "source": "amap_cache",
        })

    result["total_routes"] = len(result["routes"])

    return result



# TRIPMATE_TRANSIT_ALTERNATIVE_V1
@router.get("/{trip_id}/transit-alternative")
def get_transit_alternative(
    trip_id: int,
    version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json
    import math
    from pathlib import Path

    # Reuse existing user ownership and itinerary version checks.
    map_data = get_trip_map_data(
        trip_id=trip_id,
        version=version,
        db=db,
        current_user=current_user,
    )

    resolved_version = map_data["version"]

    cache_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "route_geometry_cache.json"
    )

    if not cache_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No cached transit alternative",
        )

    try:
        cache = json.loads(
            cache_path.read_text(encoding="utf-8-sig")
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Transit cache unreadable",
        ) from exc

    entries = cache.get("routes", {})

    if not isinstance(entries, dict):
        raise HTTPException(
            status_code=500,
            detail="Transit cache invalid",
        )

    item = entries.get(
        "trip4_v1_lingyin_to_xixi_transit"
    )

    if not isinstance(item, dict):
        raise HTTPException(
            status_code=404,
            detail="Transit alternative not found",
        )

    if (
        trip_id != 4
        or resolved_version != 1
        or item.get("trip_id") != trip_id
        or item.get("version") != resolved_version
        or item.get("transport_mode") != "public_transport"
        or item.get("source") != "amap"
    ):
        raise HTTPException(
            status_code=404,
            detail="No alternative for this itinerary",
        )

    # Verify the original itinerary actually contains this pair.
    origin = item.get("origin_name")
    destination = item.get("destination_name")

    saved_route = next(
        (
            route for route in map_data.get("routes", [])
            if route.get("origin_name") == origin
            and route.get("destination_name") == destination
            and route.get("transport_mode") == "public_transport"
        ),
        None,
    )

    if saved_route is None:
        raise HTTPException(
            status_code=404,
            detail="Original transit route not present",
        )

    segments = []
    raw_segments = item.get("segments", [])

    if not isinstance(raw_segments, list) or len(raw_segments) > 500:
        raise HTTPException(
            status_code=500,
            detail="Invalid transit segments",
        )

    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue

        mode = segment.get("mode")
        if mode not in {"walking", "bus", "subway"}:
            continue

        raw_points = segment.get("polyline")

        if (
            not isinstance(raw_points, list)
            or not 2 <= len(raw_points) <= 10000
        ):
            continue

        points = []
        valid = True

        for point in raw_points:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                valid = False
                break

            try:
                lon = float(point[0])
                lat = float(point[1])
            except (ValueError, TypeError):
                valid = False
                break

            if not (
                math.isfinite(lon)
                and math.isfinite(lat)
                and 119 < lon < 121
                and 29 < lat < 31
            ):
                valid = False
                break

            points.append([lon, lat])

        if valid:
            segments.append({
                "mode": mode,
                "name": str(segment.get("name") or ""),
                "polyline": points,
                "point_count": len(points),
            })

    if not segments:
        raise HTTPException(
            status_code=404,
            detail="No drawable transit segments",
        )

    return {
        "trip_id": trip_id,
        "version": resolved_version,
        "route_type": "alternative",
        "matches_original": bool(
            item.get("matches_saved_lines") is True
        ),
        "origin_name": origin,
        "destination_name": destination,
        "saved_duration_min": saved_route.get("duration_min"),
        "alternative_duration_min": item.get("duration_min"),
        "alternative_distance_m": item.get("distance_m"),
        "line_names": item.get("line_names", []),
        "segments": segments,
        "segment_count": len(segments),
        "source": "amap_cache",
    }
