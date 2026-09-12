"""The Leaflet bounding-box selector."""

from __future__ import annotations

from typing import Any

import reflex as rx

from ._base import Map3dComponent, asset_library

__all__ = ["Map3dAreaSelector", "map3d_area_selector"]

DEFAULT_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
DEFAULT_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
)


class Map3dAreaSelector(Map3dComponent):
    """An OpenStreetMap map on which the user drags out a bounding box.

    Switch the map into "Select Box" mode, drag a rectangle, and the selection
    is pushed to the backend through ``on_select`` as
    ``{"north": ..., "south": ..., "east": ..., "west": ...}``.
    """

    library = asset_library("area_selector.jsx")

    tag = "Map3dAreaSelector"

    # Where the map opens, as ``[lat, lng]``.
    center: rx.Var[list[float]] = rx.Var.create([40.8, -73.95])

    # The initial zoom level.
    zoom: rx.Var[int] = rx.Var.create(13)

    # The XYZ raster tile template to render.
    tile_url: rx.Var[str] = rx.Var.create(DEFAULT_TILE_URL)

    # The attribution shown in the map corner. Keep it when using OSM tiles.
    attribution: rx.Var[str] = rx.Var.create(DEFAULT_ATTRIBUTION)

    # The smallest zoom level the user may reach.
    min_zoom: rx.Var[int] = rx.Var.create(2)

    # The largest zoom level the user may reach.
    max_zoom: rx.Var[int] = rx.Var.create(19)

    # The stroke colour of the selection rectangle.
    rectangle_color: rx.Var[str] = rx.Var.create("#1f6feb")

    # Whether to render the built-in mode/clear buttons.
    show_controls: rx.Var[bool] = rx.Var.create(True)

    # Label of the button that switches into rectangle-drawing mode.
    select_label: rx.Var[str] = rx.Var.create("Select Box")

    # Label of the button that switches back to panning.
    drag_label: rx.Var[str] = rx.Var.create("Back to Drag")

    # Label of the button that clears the current selection.
    clear_label: rx.Var[str] = rx.Var.create("Remove Box")

    # Fired with the bounding box whenever the user finishes a drag.
    on_select: rx.EventHandler[lambda bbox: [bbox]]

    # Fired when the user clears the current selection.
    on_clear: rx.EventHandler[lambda: []]

    # Fired with ``True`` for pan mode and ``False`` for draw mode.
    on_mode_change: rx.EventHandler[lambda drag_enabled: [drag_enabled]]

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Map3dAreaSelector:
        """Create the selector, defaulting to a usable size.

        Leaflet needs a sized container, so a default height is applied unless
        the caller sets one.

        Args:
            *children: Extra nodes rendered on top of the map.
            **props: The component props.

        Returns:
            The component instance.
        """
        props.setdefault("height", "480px")
        props.setdefault("width", "100%")
        return super().create(*children, **props)


map3d_area_selector = Map3dAreaSelector.create
