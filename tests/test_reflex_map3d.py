"""Tests for the reflex-map3d component package."""

from __future__ import annotations

import pathlib

import httpx
import pytest
import reflex as rx
from reflex_map3d import (
    BBox,
    Map3dAreaSelector,
    Map3dScene,
    Map3dViewer,
    OverpassError,
    buildings_query,
    fetch_buildings,
    map3d_area_selector,
    map3d_scene,
    map3d_viewer,
    roads_query,
    to_bbox,
    to_features,
)
from reflex_map3d._base import FRONTEND_FILES, NPM_DEPENDENCIES
from reflex_map3d.overpass import DEFAULT_OVERPASS_URL, FALLBACK_OVERPASS_URLS, _endpoints

PACKAGE_DIR = pathlib.Path(__import__("reflex_map3d").__file__).parent


class TestBBox:
    """The bounding-box value object."""

    def test_normalises_inverted_corners(self):
        box = BBox(north=10.0, south=20.0, east=-70.0, west=-60.0)
        assert box.north == 20.0
        assert box.south == 10.0
        assert box.east == -60.0
        assert box.west == -70.0

    def test_center_and_span(self):
        box = BBox(north=40.8, south=40.6, east=-73.9, west=-74.1)
        assert box.center == pytest.approx((40.7, -74.0))
        assert box.span == pytest.approx(0.4)

    def test_is_empty(self):
        assert BBox(north=1.0, south=1.0, east=2.0, west=3.0).is_empty
        assert not BBox(north=1.0, south=0.0, east=2.0, west=3.0).is_empty

    def test_overpass_order_is_south_west_north_east(self):
        box = BBox(north=40.8, south=40.6, east=-73.9, west=-74.1)
        assert box.overpass_bbox() == "40.6,-74.1,40.8,-73.9"

    def test_to_dict_round_trips(self):
        box = BBox(north=40.8, south=40.6, east=-73.9, west=-74.1)
        assert to_bbox(box.to_dict()) == box


class TestToBBox:
    """Coercion of the shapes the frontend and OSM tooling produce."""

    def test_accepts_a_bbox(self):
        box = BBox(north=1.0, south=0.0, east=1.0, west=0.0)
        assert to_bbox(box) is box

    def test_accepts_corner_mappings(self):
        box = to_bbox([{"lat": 40.83, "lng": -73.88}, {"lat": 40.80, "lng": -73.95}])
        assert box.north == pytest.approx(40.83)
        assert box.west == pytest.approx(-73.95)

    def test_accepts_lon_spelling(self):
        box = to_bbox([{"lat": 1.0, "lon": 2.0}, {"lat": 0.0, "lon": 0.0}])
        assert box.east == pytest.approx(2.0)

    def test_accepts_pairs(self):
        box = to_bbox([(40.83, -73.88), (40.80, -73.95)])
        assert box.south == pytest.approx(40.80)

    def test_rejects_nonsense(self):
        with pytest.raises(ValueError):
            to_bbox("somewhere")
        with pytest.raises(ValueError):
            to_bbox([{"lat": 1.0, "lng": 1.0}])


class TestOverpass:
    """Query building and response parsing."""

    BBOX = {"north": 40.8, "south": 40.6, "east": -73.9, "west": -74.1}

    def test_buildings_query_covers_ways_and_relations(self):
        query = buildings_query(self.BBOX)
        assert 'way["building"](40.6,-74.1,40.8,-73.9)' in query
        assert 'relation["building"](40.6,-74.1,40.8,-73.9)' in query
        assert query.endswith("out body geom;")

    def test_roads_query_uses_highway(self):
        query = roads_query(self.BBOX, timeout=7)
        assert "[timeout:7]" in query
        assert 'way["highway"](40.6,-74.1,40.8,-73.9)' in query

    def test_to_features_renames_lon_to_lng(self):
        features = to_features(
            [
                {
                    "id": 1,
                    "type": "way",
                    "tags": {"building": "yes"},
                    "geometry": [{"lat": 1.0, "lon": 2.0}, {"lat": 3.0, "lon": 4.0}],
                }
            ]
        )
        assert features[0]["geometry"] == [
            {"lat": 1.0, "lng": 2.0},
            {"lat": 3.0, "lng": 4.0},
        ]

    def test_to_features_drops_geometryless_elements(self):
        assert to_features([{"id": 1, "tags": {}}]) == []
        assert to_features(None) == []

    def test_to_features_defaults_missing_tags(self):
        features = to_features([{"id": 1, "geometry": [{"lat": 1.0, "lon": 2.0}]}])
        assert features[0]["tags"] == {}


class TestFrontendAssets:
    """The React sources that ship inside the wheel."""

    def test_every_registered_file_exists(self):
        for name in FRONTEND_FILES:
            assert (PACKAGE_DIR / name).is_file(), name

    def test_entry_points_are_registered(self):
        for name in ("area_selector.jsx", "scene.jsx", "viewer.jsx"):
            assert name in FRONTEND_FILES

    def test_npm_dependencies_are_pinned(self):
        for dependency in NPM_DEPENDENCIES:
            assert "@" in dependency.lstrip("@"), dependency


class TestComponents:
    """The Reflex components themselves."""

    @pytest.mark.parametrize(
        ("component", "tag"),
        [
            (Map3dAreaSelector, "Map3dAreaSelector"),
            (Map3dScene, "Map3dScene"),
            (Map3dViewer, "Map3dViewer"),
        ],
    )
    def test_library_points_at_a_bundled_module(self, component, tag):
        assert component.tag == tag
        assert component.library.startswith("$/public/")
        assert component.library.endswith(".jsx")

    @pytest.mark.parametrize("factory", [map3d_area_selector, map3d_scene, map3d_viewer])
    def test_factories_apply_a_default_size(self, factory):
        component = factory()
        assert component.style.get("height") is not None
        assert component.style.get("width") is not None

    def test_scene_renders_its_props(self):
        component = map3d_scene(
            bbox={"north": 1.0, "south": 0.0, "east": 1.0, "west": 0.0},
            building_color="#ff0000",
            export_trigger=3,
        )
        rendered = str(component.render())
        assert "buildingColor" in rendered
        assert "exportTrigger" in rendered

    def test_scene_accepts_state_vars(self):
        class _State(rx.State):
            bbox: dict[str, float] = {}
            buildings: list[dict] = []

        component = map3d_scene(bbox=_State.bbox, buildings=_State.buildings)
        assert component.render() is not None

    def test_event_triggers_are_declared(self):
        triggers = map3d_scene().get_event_triggers()
        for name in ("on_building_click", "on_export", "on_load", "on_error"):
            assert name in triggers

        selector_triggers = map3d_area_selector().get_event_triggers()
        for name in ("on_select", "on_clear", "on_mode_change"):
            assert name in selector_triggers

    def test_components_are_client_side_only(self):
        # NoSSRComponent subclasses render through a dynamic import.
        assert type(map3d_scene()).__mro__[1].__name__ in {
            "Map3dComponent",
            "NoSSRComponent",
        }


class TestOverpassTransport:
    """How the HTTP request is actually shaped and retried."""

    BBOX = {"north": 40.76, "south": 40.75, "east": -73.97, "west": -73.98}

    def test_query_is_sent_as_the_data_form_field(self, monkeypatch):
        """Overpass answers 406 to a raw body; the query must be form-encoded."""
        seen = {}

        class _Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, url, data=None, headers=None):
                seen["url"] = url
                seen["data"] = data
                seen["headers"] = headers
                return httpx.Response(
                    200,
                    json={"elements": []},
                    request=httpx.Request("POST", url),
                )

        monkeypatch.setattr(httpx, "Client", _Client)
        fetch_buildings(self.BBOX)

        assert seen["url"] == DEFAULT_OVERPASS_URL
        assert set(seen["data"]) == {"data"}
        assert 'way["building"]' in seen["data"]["data"]
        assert "User-Agent" in seen["headers"]

    def test_rate_limit_falls_through_to_a_mirror(self, monkeypatch):
        calls = []

        class _Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, url, data=None, headers=None):
                calls.append(url)
                request = httpx.Request("POST", url)
                if len(calls) == 1:
                    return httpx.Response(429, text="too many", request=request)
                return httpx.Response(200, json={"elements": []}, request=request)

        monkeypatch.setattr(httpx, "Client", _Client)
        assert fetch_buildings(self.BBOX) == []
        assert calls == [DEFAULT_OVERPASS_URL, FALLBACK_OVERPASS_URLS[0]]

    def test_a_hard_error_is_raised_with_context(self, monkeypatch):
        class _Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, url, data=None, headers=None):
                return httpx.Response(400, text="parse error", request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx, "Client", _Client)
        with pytest.raises(OverpassError, match="parse error"):
            fetch_buildings(self.BBOX)

    def test_a_custom_endpoint_is_not_second_guessed(self):
        assert _endpoints("https://my.overpass/api") == ["https://my.overpass/api"]
        assert _endpoints(DEFAULT_OVERPASS_URL)[1:] == list(FALLBACK_OVERPASS_URLS)
