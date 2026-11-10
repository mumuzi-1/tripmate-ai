import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

load_dotenv(
    Path(__file__).resolve().parents[3] / ".env",
    override=False,
)

router = APIRouter()

# Only allow known Amap API path families.
ALLOWED_PATH = re.compile(
    r"^v(?:3|4|5)/[A-Za-z0-9/_.,-]+$"
)


@router.get("/_AMapService/{path:path}")
async def amap_js_proxy(path: str, request: Request):
    if not ALLOWED_PATH.fullmatch(path):
        raise HTTPException(
            status_code=404,
            detail="Unsupported Amap service path",
        )

    security_code = os.getenv("AMAP_SECURITY_JS_CODE")

    if not security_code:
        raise HTTPException(
            status_code=503,
            detail="Amap JS security is not configured",
        )

    # Amap custom map styles use webapi.amap.com.
    if path.startswith("v4/map/styles"):
        upstream = "https://webapi.amap.com"
    else:
        upstream = "https://restapi.amap.com"

    # Do not accept a caller-supplied security code.
    params = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key.lower() != "jscode"
    ]
    params.append(("jscode", security_code))

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            result = await client.get(
                f"{upstream}/{path}",
                params=params,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Amap upstream service unavailable",
        ) from exc

    headers = {}

    for name in ("content-type", "cache-control"):
        value = result.headers.get(name)
        if value:
            headers[name] = value

    return Response(
        content=result.content,
        status_code=result.status_code,
        headers=headers,
    )
