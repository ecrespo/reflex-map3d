"""The react-three-fiber 3D city scene."""

from __future__ import annotations

from typing import Any

import reflex as rx

from ._base import Map3dComponent, asset_library
from .overpass import DEFAULT_OVERPASS_URL

__all__ = ["DEFAULT_SCALE", "Map3dScene", "map3d_scene"]

#: World units per degree of latitude, as used by cartesiancs/map3d.
DEFAULT_SCALE = 51000


class Map3dScene(Map3dComponent):
    """A 3D city built from OpenStreetMap footprints.

    Buildings are extruded polygons and roads are centre lines, both projected
    around the centre of ``bbox``. Feed it ``buildings``/``roads`` from the
    Reflex state (see :mod:`reflex_map3d.overpass`) or set ``auto_fetch`` and
    let the browser query Overpass directly.
    """

    library = asset_library("scene.jsx")

    tag = "Map3dScene"

    # The area the scene is projected around, as
    # ``{"north": ..., "south": ..., "east": ..., "west": ...}``.
    bbox: rx.Var[dict[str, float] | None] = rx.Var.create(None)

    # The buildings to render: ``{"id", "tags", "geometry": [{"lat", "lng"}]}``.
    buildings: rx.Var[list[dict[str, Any]]] = rx.Var.create([])

    # The roads to render, in the same shape as ``buildings``.
    roads: rx.Var[list[dict[str, Any]]] = rx.Var.create([])

    # Fetch buildings in the browser when ``buildings`` is empty.
    auto_fetch: rx.Var[bool] = rx.Var.create(False)

    # Fetch roads in the browser when ``roads`` is empty.
    fetch_roads_from_overpass: rx.Var[bool] = rx.Var.create(False)

    # The Overpass endpoint used by the browser-side fetches.
    overpass_url: rx.Var[str] = rx.Var.create(DEFAULT_OVERPASS_URL)

    # The Overpass server-side timeout in seconds.
    overpass_timeout: rx.Var[int] = rx.Var.create(25)

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

    # How far above the ground plane the roads are drawn.
    road_elevation: rx.Var[float] = rx.Var.create(0.1)

    # Whether roads are rendered at all.
    show_roads: rx.Var[bool] = rx.Var.create(True)

    # Whether hovering a building opens its OpenStreetMap tag panel.
    show_tooltip: rx.Var[bool] = rx.Var.create(True)

    # Whether the drei sky dome is rendered.
    show_sky: rx.Var[bool] = rx.Var.create(True)

    # Whether an image-based lighting environment is applied.
    show_environment: rx.Var[bool] = rx.Var.create(True)

    # The drei environment preset ("city", "sunset", "dawn", "night", ...).
    environment_preset: rx.Var[str] = rx.Var.create("city")

    # A solid canvas background colour. Leave unset for a transparent canvas.
    background: rx.Var[str | None] = rx.Var.create(None)

    # Whether orbit controls are attached when drive mode is off.
    orbit_controls: rx.Var[bool] = rx.Var.create(True)

    # Whether to drive a car through the city with WASD instead of orbiting.
    drive_mode: rx.Var[bool] = rx.Var.create(False)

    # Top speed of the car in drive mode.
    drive_speed: rx.Var[float] = rx.Var.create(3.0)

    # The colour of the car in drive mode.
    drive_color: rx.Var[str] = rx.Var.create("orange")

    # The camera field of view in degrees.
    camera_fov: rx.Var[float] = rx.Var.create(90.0)

    # The camera near clipping plane.
    camera_near: rx.Var[float] = rx.Var.create(0.1)

    # The camera far clipping plane.
    camera_far: rx.Var[float] = rx.Var.create(7000.0)

    # The initial camera position as ``[x, y, z]``.
    camera_position: rx.Var[list[float]] = rx.Var.create([0.0, 120.0, 260.0])

    # Pull the camera back to frame the whole area once buildings arrive.
    auto_frame: rx.Var[bool] = rx.Var.create(True)

    # The intensity of the ambient light.
    ambient_intensity: rx.Var[float] = rx.Var.create(1.5707963267948966)

    # Increment this to export the scene as GLB. Any change triggers a download.
    export_trigger: rx.Var[int] = rx.Var.create(0)

    # The file name of the exported GLB.
    export_filename: rx.Var[str] = rx.Var.create("scene.glb")

    # Fired with ``{"id", "tags", "selected"}`` when a building is clicked.
    on_building_click: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"id", "tags"}`` when a building is hovered.
    on_building_hover: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"filename", "bytes"}`` once a GLB export finishes.
    on_export: rx.EventHandler[lambda info: [info]]

    # Fired with ``{"buildings", "roads"}`` whenever the rendered counts change.
    on_load: rx.EventHandler[lambda info: [info]]

    # Fired with an error message when a fetch or an export fails.
    on_error: rx.EventHandler[lambda message: [message]]

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Map3dScene:
        """Create the scene, defaulting to a usable size.

        A WebGL canvas collapses inside an unsized parent, so a default height
        is applied unless the caller sets one.

        Args:
            *children: Nodes rendered as an overlay above the canvas.
            **props: The component props.

        Returns:
            The component instance.
        """
        props.setdefault("height", "600px")
        props.setdefault("width", "100%")
        return super().create(*children, **props)


map3d_scene = Map3dScene.create
