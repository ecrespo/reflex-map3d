"""Server-side OpenStreetMap access for reflex-map3d.

The frontend components can fetch from Overpass themselves, but doing it from
the Reflex backend keeps the data in the app state, where it can be cached,
filtered, persisted or post-processed before it ever reaches the browser.
"""

from __future__ import annotations

from typing import Any

import httpx

from .models import BBox, Feature, to_bbox

__all__ = [
    "DEFAULT_OVERPASS_URL",
    "FALLBACK_OVERPASS_URLS",
    "OverpassError",
    "buildings_query",
    "fetch_buildings",
    "fetch_buildings_async",
    "fetch_roads",
    "fetch_roads_async",
    "roads_query",
    "to_features",
]

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

#: Public mirrors to fall back to when the primary endpoint rate-limits.
FALLBACK_OVERPASS_URLS: tuple[str, ...] = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

#: Overpass rejects anonymous clients with 406/429, so identify the caller.
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "reflex-map3d (+https://github.com/ecrespo/reflex-map3d)",
}

#: Status codes worth retrying on another mirror rather than surfacing.
_RETRYABLE = frozenset({429, 502, 503, 504})


class OverpassError(RuntimeError):
    """Raised when every Overpass endpoint refuses the query."""


def buildings_query(bbox: Any, timeout: int = 25) -> str:
    """Build the Overpass QL query for every building inside ``bbox``.

    Args:
        bbox: The area, in any shape :func:`~reflex_map3d.models.to_bbox` accepts.
        timeout: The Overpass server-side timeout in seconds.

    Returns:
        The Overpass QL query string.
    """
    box = to_bbox(bbox).overpass_bbox()
    return (
        f"[out:json][timeout:{timeout}];"
        f'(way["building"]({box});relation["building"]({box}););'
        f"out body geom;"
    )


def roads_query(bbox: Any, timeout: int = 25) -> str:
    """Build the Overpass QL query for every road inside ``bbox``.

    Args:
        bbox: The area, in any shape :func:`~reflex_map3d.models.to_bbox` accepts.
        timeout: The Overpass server-side timeout in seconds.

    Returns:
        The Overpass QL query string.
    """
    box = to_bbox(bbox).overpass_bbox()
    return f'[out:json][timeout:{timeout}];(way["highway"]({box}););out body geom;'


def to_features(elements: Any) -> list[Feature]:
    """Convert raw Overpass elements into the shape the components render.

    Elements without usable geometry are dropped.

    Args:
        elements: The ``elements`` list of an Overpass JSON response.

    Returns:
        A list of ``{"id", "type", "tags", "geometry"}`` dicts.
    """
    features: list[Feature] = []
    for element in elements or []:
        geometry = [
            {"lat": float(point["lat"]), "lng": float(point["lon"])}
            for point in element.get("geometry") or []
            if point.get("lat") is not None and point.get("lon") is not None
        ]
        if not geometry:
            continue
        features.append(
            {
                "id": element.get("id"),
                "type": element.get("type"),
                "tags": element.get("tags") or {},
                "geometry": geometry,
            }
        )
    return features


def _endpoints(url: str) -> list[str]:
    """The endpoints to try, primary first.

    Args:
        url: The endpoint the caller asked for.

    Returns:
        The ordered list of endpoints, with the public mirrors appended when
        the caller did not name a custom one.
    """
    if url != DEFAULT_OVERPASS_URL:
        return [url]
    return [url, *FALLBACK_OVERPASS_URLS]


def _parse(response: httpx.Response) -> list[Feature]:
    """Turn a successful Overpass response into features.

    Args:
        response: The HTTP response.

    Returns:
        The parsed features.

    Raises:
        OverpassError: If the body is not the JSON Overpass promised.
    """
    try:
        payload = response.json()
    except ValueError as exc:
        preview = response.text[:200].strip()
        msg = f"Overpass returned a non-JSON response: {preview}"
        raise OverpassError(msg) from exc
    return to_features(payload.get("elements"))


def _failure(url: str, response: httpx.Response) -> OverpassError:
    """Build a readable error for a refused request.

    Args:
        url: The endpoint that refused.
        response: The refusing response.

    Returns:
        The error to raise.
    """
    if response.status_code == 429:
        detail = "rate limited — wait a moment or use your own Overpass instance"
    elif response.status_code == 504:
        detail = "timed out — try a smaller area"
    elif response.status_code == 400:
        detail = f"rejected the query: {response.text[:200].strip()}"
    else:
        detail = response.text[:200].strip() or response.reason_phrase
    return OverpassError(f"Overpass {response.status_code} from {url}: {detail}")


def _run(query: str, url: str, request_timeout: float) -> list[Feature]:
    last: OverpassError | None = None
    with httpx.Client(timeout=request_timeout, follow_redirects=True) as client:
        for endpoint in _endpoints(url):
            try:
                response = client.post(endpoint, data={"data": query}, headers=_HEADERS)
            except httpx.HTTPError as exc:  # network-level failure: try the next
                last = OverpassError(f"Overpass request to {endpoint} failed: {exc}")
                continue
            if response.status_code in _RETRYABLE:
                last = _failure(endpoint, response)
                continue
            if response.is_error:
                raise _failure(endpoint, response)
            return _parse(response)
    raise last or OverpassError("No Overpass endpoint available.")


async def _run_async(query: str, url: str, request_timeout: float) -> list[Feature]:
    last: OverpassError | None = None
    async with httpx.AsyncClient(timeout=request_timeout, follow_redirects=True) as client:
        for endpoint in _endpoints(url):
            try:
                response = await client.post(endpoint, data={"data": query}, headers=_HEADERS)
            except httpx.HTTPError as exc:  # network-level failure: try the next
                last = OverpassError(f"Overpass request to {endpoint} failed: {exc}")
                continue
            if response.status_code in _RETRYABLE:
                last = _failure(endpoint, response)
                continue
            if response.is_error:
                raise _failure(endpoint, response)
            return _parse(response)
    raise last or OverpassError("No Overpass endpoint available.")


def fetch_buildings(
    bbox: Any,
    url: str = DEFAULT_OVERPASS_URL,
    timeout: int = 25,
    request_timeout: float = 60.0,
) -> list[Feature]:
    """Fetch every building inside ``bbox`` from Overpass.

    Args:
        bbox: The area to query.
        url: The Overpass endpoint.
        timeout: The Overpass server-side timeout in seconds.
        request_timeout: The HTTP client timeout in seconds.

    Returns:
        The buildings, ready to hand to ``map3d_scene``.
    """
    return _run(buildings_query(bbox, timeout), url, request_timeout)


def fetch_roads(
    bbox: Any,
    url: str = DEFAULT_OVERPASS_URL,
    timeout: int = 25,
    request_timeout: float = 60.0,
) -> list[Feature]:
    """Fetch every road inside ``bbox`` from Overpass.

    Args:
        bbox: The area to query.
        url: The Overpass endpoint.
        timeout: The Overpass server-side timeout in seconds.
        request_timeout: The HTTP client timeout in seconds.

    Returns:
        The roads, ready to hand to ``map3d_scene``.
    """
    return _run(roads_query(bbox, timeout), url, request_timeout)


async def fetch_buildings_async(
    bbox: Any,
    url: str = DEFAULT_OVERPASS_URL,
    timeout: int = 25,
    request_timeout: float = 60.0,
) -> list[Feature]:
    """Asynchronously fetch every building inside ``bbox``.

    Args:
        bbox: The area to query.
        url: The Overpass endpoint.
        timeout: The Overpass server-side timeout in seconds.
        request_timeout: The HTTP client timeout in seconds.

    Returns:
        The buildings, ready to hand to ``map3d_scene``.
    """
    return await _run_async(buildings_query(bbox, timeout), url, request_timeout)


async def fetch_roads_async(
    bbox: Any,
    url: str = DEFAULT_OVERPASS_URL,
    timeout: int = 25,
    request_timeout: float = 60.0,
) -> list[Feature]:
    """Asynchronously fetch every road inside ``bbox``.

    Args:
        bbox: The area to query.
        url: The Overpass endpoint.
        timeout: The Overpass server-side timeout in seconds.
        request_timeout: The HTTP client timeout in seconds.

    Returns:
        The roads, ready to hand to ``map3d_scene``.
    """
    return await _run_async(roads_query(bbox, timeout), url, request_timeout)


__all__ += ["BBox"]
