"""The all-in-one map3d workflow component."""

from __future__ import annotations

from typing import Any

import reflex as rx

from ._base import Map3dComponent, asset_library
from .area_selector import DEFAULT_ATTRIBUTION, DEFAULT_TILE_URL
from .overpass import DEFAULT_OVERPASS_URL
from .scene import DEFAULT_SCALE

__all__ = ["Map3dViewer", "map3d_viewer"]


class Map3dViewer(Map3dComponent):
    """The complete map3d experience in a single component.

    Walks the user through picking an area on a Leaflet map, downloading the
    OpenStreetMap data for it, exploring the generated 3D city and exporting it
    as a GLB file. Every step also reports back to the Reflex state, so the app
    can mirror the selection, the counts and the export.
    """

    library = asset_library("viewer.jsx")

    tag = "Map3dViewer"

    # Where the map opens, as ``[lat, lng]``.
    center: rx.Var[list[float]] = rx.Var.create([40.8, -73.95])

    # The initial zoom level.
    zoom: rx.Var[int] = rx.Var.create(13)

    # The XYZ raster tile template to render.
    tile_url: rx.Var[str] = rx.Var.create(DEFAULT_TILE_URL)

    # The attribution shown in the map corner.
    attribution: rx.Var[str] = rx.Var.create(DEFAULT_ATTRIBUTION)

    # The Overpass endpoint the viewer downloads from.
    overpass_url: rx.Var[str] = rx.Var.create(DEFAULT_OVERPASS_URL)

    # The Overpass server-side timeout in seconds.
    overpass_timeout: rx.Var[int] = rx.Var.create(25)

    # Whether road centre lines are downloaded and rendered.
    include_roads: rx.Var[bool] = rx.Var.create(True)

    # Area size in degrees (dlat + dlng) above which the viewer warns first.
    max_span: rx.Var[float] = rx.Var.create(0.1)

    # World units per degree of latitude.
    scale: rx.Var[int] = rx.Var.create(DEFAULT_SCALE)

    # Height in metres for buildings with no height information.
    default_height: rx.Var[float] = rx.Var.create(10.0)

    # Metres per floor, used when a building only tags ``building:levels``.
    level_height: rx.Var[float] = rx.Var.create(2.2)

    # The colour of an idle building.
    building_color: rx.Var[str] = rx.Var.create("#9da0a3")

    # The colour of a hovered or selected building.
    highlight_color: rx.Var[str] = rx.Var.create("#007bff")

    # The colour of the road lines.
    road_color: rx.Var[str] = rx.Var.create("#34f516")

    # The width of the road lines.
    road_width: rx.Var[float] = rx.Var.create(1.0)

    # Whether hovering a building opens its OpenStreetMap tag panel.
    show_tooltip: rx.Var[bool] = rx.Var.create(True)

    # Whether the drei sky dome is rendered.
    show_sky: rx.Var[bool] = rx.Var.create(True)

    # Whether an image-based lighting environment is applied.
    show_environment: rx.Var[bool] = rx.Var.create(True)

    # The drei environment preset ("city", "sunset", "dawn", "night", ...).
    environment_preset: rx.Var[str] = rx.Var.create("city")

    # Whether to drive a car through the city with WASD instead of orbiting.
    drive_mode: rx.Var[bool] = rx.Var.create(False)

    # The file name of the exported GLB.
    export_filename: rx.Var[str] = rx.Var.create("scene.glb")

    # The heading shown on the area-selection step.
    title: rx.Var[str] = rx.Var.create("Generate 3D map")

    # The paragraph shown on the area-selection step.
    description: rx.Var[str] = rx.Var.create(
        "Draw a box over the map to pick an area, then build it in 3D and export it as GLB."
    )

    # Fired with the bounding box whenever the user finishes a drag.
    on_select: rx.EventHandler[lambda bbox: [bbox]]

    # Fired with ``{"buildings", "roads", "bbox"}`` once the data is downloaded.
    on_load: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"filename", "bytes"}`` once a GLB export finishes.
    on_export: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"step", "name"}`` when the workflow advances.
    on_step_change: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"id", "tags", "selected"}`` when a building is clicked.
    on_building_click: rx.EventHandler[lambda info: [info]]

    # Fired with an error message when a fetch or an export fails.
    on_error: rx.EventHandler[lambda message: [message]]

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Map3dViewer:
        """Create the viewer, defaulting to a usable size.

        Args:
            *children: Extra nodes rendered inside the viewer shell.
            **props: The component props.

        Returns:
            The component instance.
        """
        props.setdefault("height", "100vh")
        props.setdefault("width", "100%")
        return super().create(*children, **props)


map3d_viewer = Map3dViewer.create
