"""Reflex custom component: map3d.

Generate a real-world 3D city from OpenStreetMap data, straight from a Reflex
app. A port of https://github.com/cartesiancs/map3d.
"""

from ._base import NPM_DEPENDENCIES
from .area_selector import (
    DEFAULT_ATTRIBUTION,
    DEFAULT_TILE_URL,
    Map3dAreaSelector,
    map3d_area_selector,
)
from .models import BBox, Feature, to_bbox
from .overpass import (
    DEFAULT_OVERPASS_URL,
    FALLBACK_OVERPASS_URLS,
    OverpassError,
    buildings_query,
    fetch_buildings,
    fetch_buildings_async,
    fetch_roads,
    fetch_roads_async,
    roads_query,
    to_features,
)
from .scene import DEFAULT_SCALE, Map3dScene, map3d_scene
from .viewer import Map3dViewer, map3d_viewer

__all__ = [
    "DEFAULT_ATTRIBUTION",
    "DEFAULT_OVERPASS_URL",
    "DEFAULT_SCALE",
    "DEFAULT_TILE_URL",
    "FALLBACK_OVERPASS_URLS",
    "NPM_DEPENDENCIES",
    "BBox",
    "Feature",
    "Map3dAreaSelector",
    "Map3dScene",
    "Map3dViewer",
    "OverpassError",
    "buildings_query",
    "fetch_buildings",
    "fetch_buildings_async",
    "fetch_roads",
    "fetch_roads_async",
    "map3d_area_selector",
    "map3d_scene",
    "map3d_viewer",
    "roads_query",
    "to_bbox",
    "to_features",
]

__version__ = "0.1.0"
