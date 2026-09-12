"""Demo app for the reflex-map3d custom component.

Three pages, one per way of using the component:

* ``/``         — the selector and the scene wired together through Reflex state,
                  with the OpenStreetMap download happening on the backend.
* ``/viewer``   — the all-in-one ``map3d_viewer`` workflow.
* ``/presets``  — the scene alone, fed from preset city bounding boxes.
* ``/offline``  — the scene with synthetic geometry and no network access.
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex_map3d import (
    BBox,
    fetch_buildings_async,
    fetch_roads_async,
    map3d_area_selector,
    map3d_scene,
    map3d_viewer,
    to_bbox,
)

ACCENT = "#1f6feb"

PRESETS: dict[str, dict[str, float]] = {
    "Manhattan — Midtown": {
        "north": 40.7620,
        "south": 40.7500,
        "east": -73.9740,
        "west": -73.9880,
    },
    "Paris — Louvre": {
        "north": 48.8660,
        "south": 48.8570,
        "east": 2.3450,
        "west": 2.3290,
    },
    "Caracas — Altamira": {
        "north": 10.4990,
        "south": 10.4910,
        "east": -66.8460,
        "west": -66.8580,
    },
    "Barcelona — Eixample": {
        "north": 41.3960,
        "south": 41.3880,
        "east": 2.1720,
        "west": 2.1580,
    },
    "Tokyo — Shinjuku": {
        "north": 35.6960,
        "south": 35.6880,
        "east": 139.7060,
        "west": 139.6930,
    },
}


class State(rx.State):
    """State for the composed demo page."""

    bbox: dict[str, float] | None = None
    buildings: list[dict[str, Any]] = []
    roads: list[dict[str, Any]] = []
    include_roads: bool = True
    drive_mode: bool = False
    loading: bool = False
    error: str = ""
    selected: dict[str, str] = {}
    selected_name: str = ""
    export_trigger: int = 0
    last_export: str = ""

    @rx.var
    def has_area(self) -> bool:
        """Whether a usable area has been selected."""
        if not self.bbox:
            return False
        box = BBox(**self.bbox)
        return not box.is_empty

    @rx.var
    def area_label(self) -> str:
        """A human-readable summary of the selected area."""
        if not self.bbox:
            return "No area selected yet — drag a box on the map."
        box = BBox(**self.bbox)
        lat, lng = box.center
        return f"center {lat:.4f}, {lng:.4f}  ·  span {box.span:.4f}°"

    @rx.var
    def counts_label(self) -> str:
        """A human-readable summary of what was downloaded."""
        if not self.buildings and not self.roads:
            return "Nothing downloaded yet."
        return f"{len(self.buildings)} buildings · {len(self.roads)} roads"

    @rx.event
    def toggle_roads(self, value: bool) -> None:
        """Show or hide road centre lines.

        Args:
            value: Whether roads should be rendered.
        """
        self.include_roads = value

    @rx.event
    def toggle_drive(self, value: bool) -> None:
        """Switch between orbit controls and drive mode.

        Args:
            value: Whether drive mode is on.
        """
        self.drive_mode = value

    @rx.event
    def select_area(self, bbox: dict[str, float]) -> None:
        """Store the bounding box the selector reported.

        Args:
            bbox: The selected area.
        """
        self.bbox = to_bbox(bbox).to_dict()
        self.buildings = []
        self.roads = []
        self.error = ""

    @rx.event
    def clear_area(self) -> None:
        """Forget the current selection and its data."""
        self.bbox = None
        self.buildings = []
        self.roads = []
        self.error = ""

    @rx.event(background=True)
    async def load(self):
        """Download the OpenStreetMap data for the selected area."""
        async with self:
            if not self.bbox or self.loading:
                return
            self.loading = True
            self.error = ""
            area = dict(self.bbox)
            want_roads = self.include_roads

        try:
            buildings = await fetch_buildings_async(area)
            roads = await fetch_roads_async(area) if want_roads else []
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            async with self:
                self.error = f"Overpass request failed: {exc}"
                self.loading = False
            return

        async with self:
            self.buildings = buildings
            self.roads = roads
            self.loading = False

    @rx.event
    def pick_building(self, info: dict[str, Any]) -> None:
        """Remember the building the user clicked.

        Args:
            info: The ``{"id", "tags", "selected"}`` payload from the scene.
        """
        tags = info.get("tags") or {}
        self.selected = {str(k): str(v) for k, v in tags.items()}
        self.selected_name = str(tags.get("name") or f"Building {info.get('id', '')}")

    @rx.event
    def export_glb(self) -> None:
        """Ask the scene to export itself as a GLB download."""
        self.export_trigger += 1

    @rx.event
    def note_export(self, info: dict[str, Any]) -> None:
        """Record the result of a GLB export.

        Args:
            info: The ``{"filename", "bytes"}`` payload from the scene.
        """
        size = int(info.get("bytes") or 0)
        self.last_export = f"{info.get('filename', 'scene.glb')} — {size / 1024:.0f} KB"

    @rx.event
    def report_error(self, message: str) -> None:
        """Surface a frontend error.

        Args:
            message: The error message.
        """
        self.error = message


class PresetState(rx.State):
    """State for the preset-cities page."""

    name: str = "Manhattan — Midtown"
    buildings: list[dict[str, Any]] = []
    roads: list[dict[str, Any]] = []
    loading: bool = False
    error: str = ""

    @rx.var
    def bbox(self) -> dict[str, float]:
        """The bounding box of the selected preset."""
        return PRESETS[self.name]

    @rx.var
    def counts_label(self) -> str:
        """A human-readable summary of what was downloaded."""
        if not self.buildings:
            return "Press Load to download this area."
        return f"{len(self.buildings)} buildings · {len(self.roads)} roads"

    @rx.event
    def choose(self, name: str) -> None:
        """Switch to another preset city.

        Args:
            name: The preset key.
        """
        self.name = name
        self.buildings = []
        self.roads = []
        self.error = ""

    @rx.event(background=True)
    async def load(self):
        """Download the OpenStreetMap data for the selected preset."""
        async with self:
            if self.loading:
                return
            self.loading = True
            self.error = ""
            area = PRESETS[self.name]

        try:
            buildings = await fetch_buildings_async(area)
            roads = await fetch_roads_async(area)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            async with self:
                self.error = f"Overpass request failed: {exc}"
                self.loading = False
            return

        async with self:
            self.buildings = buildings
            self.roads = roads
            self.loading = False


def navbar(active: str) -> rx.Component:
    """Render the top navigation.

    Args:
        active: The route of the current page.

    Returns:
        The navbar component.
    """
    def link(label: str, href: str) -> rx.Component:
        return rx.link(
            rx.text(
                label,
                weight="medium",
                color=ACCENT if href == active else rx.color("gray", 11),
            ),
            href=href,
        )

    return rx.hstack(
        rx.hstack(
            rx.text("🗺️", font_size="1.2em"),
            rx.heading("reflex-map3d", size="4"),
            rx.badge("demo", color_scheme="blue", variant="soft"),
            align="center",
            spacing="2",
        ),
        rx.spacer(),
        rx.hstack(
            link("Composed", "/"),
            link("All-in-one", "/viewer"),
            link("Presets", "/presets"),
            link("Offline", "/offline"),
            rx.link(
                rx.text("GitHub", weight="medium", color=rx.color("gray", 11)),
                href="https://github.com/ecrespo/reflex-map3d",
                is_external=True,
            ),
            spacing="5",
            align="center",
        ),
        rx.color_mode.button(),
        width="100%",
        padding="0.75rem 1.25rem",
        align="center",
        border_bottom=f"1px solid {rx.color('gray', 5)}",
        background=rx.color("gray", 1),
    )


def stat(label: str, value: rx.Var | str) -> rx.Component:
    """Render a small labelled statistic.

    Args:
        label: The caption.
        value: The value to show.

    Returns:
        The stat component.
    """
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10)),
        rx.text(value, size="2", weight="bold"),
        spacing="0",
        align="start",
    )


def index() -> rx.Component:
    """The composed page: selector + backend fetch + scene."""
    return rx.vstack(
        navbar("/"),
        rx.vstack(
            rx.heading("Selector and scene, wired through Reflex state", size="6"),
            rx.text(
                "The bounding box travels to the backend, Overpass is queried "
                "from Python, and the buildings are handed back to the 3D scene "
                "as plain state. Drag a box, load it, then orbit the result.",
                color=rx.color("gray", 11),
                max_width="70ch",
            ),
            rx.grid(
                rx.vstack(
                    map3d_area_selector(
                        center=[40.756, -73.981],
                        zoom=14,
                        on_select=State.select_area,
                        on_clear=State.clear_area,
                        height="420px",
                        border_radius="12px",
                        overflow="hidden",
                        border=f"1px solid {rx.color('gray', 5)}",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(State.loading, "Loading…", "Load OpenStreetMap data"),
                            on_click=State.load,
                            disabled=~State.has_area | State.loading,
                            loading=State.loading,
                        ),
                        rx.checkbox(
                            "Roads",
                            checked=State.include_roads,
                            on_change=State.toggle_roads,
                        ),
                        rx.checkbox(
                            "Drive mode (WASD)",
                            checked=State.drive_mode,
                            on_change=State.toggle_drive,
                        ),
                        rx.spacer(),
                        rx.button(
                            "Export GLB",
                            on_click=State.export_glb,
                            variant="soft",
                            disabled=State.buildings.length() == 0,
                        ),
                        width="100%",
                        align="center",
                        spacing="3",
                        wrap="wrap",
                    ),
                    rx.hstack(
                        stat("Area", State.area_label),
                        rx.spacer(),
                        stat("Downloaded", State.counts_label),
                        width="100%",
                    ),
                    rx.cond(
                        State.error != "",
                        rx.callout(State.error, icon="triangle_alert", color_scheme="red"),
                    ),
                    rx.cond(
                        State.last_export != "",
                        rx.callout(
                            f"Exported {State.last_export}",
                            icon="download",
                            color_scheme="green",
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.vstack(
                    map3d_scene(
                        bbox=State.bbox,
                        buildings=State.buildings,
                        roads=State.roads,
                        show_roads=State.include_roads,
                        drive_mode=State.drive_mode,
                        export_trigger=State.export_trigger,
                        export_filename="map3d-demo.glb",
                        on_building_click=State.pick_building,
                        on_export=State.note_export,
                        on_error=State.report_error,
                        height="420px",
                        border_radius="12px",
                        overflow="hidden",
                        border=f"1px solid {rx.color('gray', 5)}",
                        background="#dfe6ee",
                    ),
                    rx.cond(
                        State.selected_name != "",
                        rx.vstack(
                            rx.heading(State.selected_name, size="3"),
                            rx.scroll_area(
                                rx.vstack(
                                    rx.foreach(
                                        State.selected,
                                        lambda item: rx.hstack(
                                            rx.text(item[0], size="1", color=rx.color("gray", 10)),
                                            rx.spacer(),
                                            rx.text(item[1], size="1"),
                                            width="100%",
                                        ),
                                    ),
                                    spacing="1",
                                    width="100%",
                                ),
                                height="150px",
                                width="100%",
                            ),
                            width="100%",
                            padding="0.75rem",
                            border_radius="10px",
                            border=f"1px solid {rx.color('gray', 5)}",
                            align="start",
                        ),
                        rx.text(
                            "Click a building to inspect its OpenStreetMap tags.",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                    ),
                    spacing="3",
                    width="100%",
                ),
                columns=rx.breakpoints(initial="1", lg="2"),
                spacing="5",
                width="100%",
            ),
            spacing="4",
            padding="1.5rem",
            width="100%",
            max_width="1400px",
        ),
        spacing="0",
        width="100%",
        align="center",
    )


def viewer_page() -> rx.Component:
    """The all-in-one viewer page."""
    return rx.vstack(
        navbar("/viewer"),
        rx.box(
            map3d_viewer(
                center=[41.3874, 2.1686],
                zoom=15,
                export_filename="barcelona.glb",
                title="Generate 3D map",
                description=(
                    "Everything the upstream map3d app does, in one Reflex "
                    "component: pick an area, download it, explore it, export it."
                ),
                height="100%",
                width="100%",
            ),
            width="100%",
            height="calc(100vh - 60px)",
        ),
        spacing="0",
        width="100%",
    )


def presets_page() -> rx.Component:
    """The preset-cities page."""
    return rx.vstack(
        navbar("/presets"),
        rx.vstack(
            rx.heading("Preset areas", size="6"),
            rx.text(
                "No map picker at all — the scene is driven entirely by a "
                "bounding box held in Python.",
                color=rx.color("gray", 11),
            ),
            rx.hstack(
                rx.select(
                    list(PRESETS),
                    value=PresetState.name,
                    on_change=PresetState.choose,
                ),
                rx.button(
                    rx.cond(PresetState.loading, "Loading…", "Load"),
                    on_click=PresetState.load,
                    loading=PresetState.loading,
                ),
                rx.text(PresetState.counts_label, size="2", color=rx.color("gray", 10)),
                align="center",
                spacing="3",
                wrap="wrap",
            ),
            rx.cond(
                PresetState.error != "",
                rx.callout(PresetState.error, icon="triangle_alert", color_scheme="red"),
            ),
            map3d_scene(
                bbox=PresetState.bbox,
                buildings=PresetState.buildings,
                roads=PresetState.roads,
                environment_preset="sunset",
                building_color="#b9bec4",
                highlight_color="#f97316",
                road_color="#6ee7ff",
                height="calc(100vh - 240px)",
                min_height="420px",
                border_radius="12px",
                overflow="hidden",
                border=f"1px solid {rx.color('gray', 5)}",
            ),
            spacing="4",
            padding="1.5rem",
            width="100%",
            max_width="1400px",
        ),
        spacing="0",
        width="100%",
        align="center",
    )


def _synthetic_city() -> list[dict[str, Any]]:
    """A grid of fake buildings, used to smoke-test rendering offline."""
    out = []
    for i in range(6):
        for j in range(6):
            lat0 = 40.7580 + i * 0.0006
            lng0 = -73.9820 + j * 0.0008
            out.append(
                {
                    "id": i * 10 + j,
                    "tags": {"building": "yes", "height": str(10 + (i + j) * 6), "name": f"B{i}{j}"},
                    "geometry": [
                        {"lat": lat0, "lng": lng0},
                        {"lat": lat0 + 0.0004, "lng": lng0},
                        {"lat": lat0 + 0.0004, "lng": lng0 + 0.0005},
                        {"lat": lat0, "lng": lng0 + 0.0005},
                    ],
                }
            )
    return out


def offline_page() -> rx.Component:
    """The scene with hand-written geometry and no network at all."""
    return rx.vstack(
        navbar("/offline"),
        rx.vstack(
            rx.heading("Offline — geometry straight from Python", size="6"),
            rx.text(
                "No tiles, no Overpass, no CDN: a grid of synthetic footprints "
                "built in a list comprehension and handed to the scene. This is "
                "the exact data shape map3d_scene expects.",
                color=rx.color("gray", 11),
                max_width="70ch",
            ),
            map3d_scene(
                bbox={"north": 40.7625, "south": 40.7575, "east": -73.9765, "west": -73.9825},
                buildings=_synthetic_city(),
                show_environment=False,
                show_sky=False,
                show_roads=False,
                background="#101820",
                building_color="#8ab4f8",
                highlight_color="#facc15",
                height="calc(100vh - 220px)",
                min_height="420px",
                border_radius="12px",
                overflow="hidden",
            ),
            spacing="4",
            padding="1.5rem",
            width="100%",
            max_width="1400px",
        ),
        spacing="0",
        width="100%",
        align="center",
    )


app = rx.App()
app.add_page(index, route="/", title="reflex-map3d · composed")
app.add_page(viewer_page, route="/viewer", title="reflex-map3d · all-in-one")
app.add_page(presets_page, route="/presets", title="reflex-map3d · presets")
app.add_page(offline_page, route="/offline", title="reflex-map3d · offline")
