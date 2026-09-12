# reflex-map3d

Generate a real-world 3D city from OpenStreetMap data, inside a [Reflex](https://reflex.dev) app.

This is a port of [cartesiancs/map3d](https://github.com/cartesiancs/map3d) — a
React-Three-Fiber 3D building mapper — to Reflex custom components. You pick an
area on a Leaflet map, the buildings and roads come from the Overpass API, the
scene is extruded in three.js, and the result can be exported as a GLB file for
Blender, Unreal, a digital twin, drone survey work or GPS-marker overlays.

![map3d](https://raw.githubusercontent.com/cartesiancs/map3d/main/.github/screenshot.png)

## Install

```bash
pip install reflex-map3d
```

The npm side (`three`, `@react-three/fiber`, `@react-three/drei`,
`react-leaflet`, `leaflet`) is installed automatically by Reflex the first time
the app compiles. There is no npm package to add by hand: the React sources ship
inside the wheel and are compiled by the app's own Vite build.

## Quick start

The whole workflow in one component:

```python
import reflex as rx
from reflex_map3d import map3d_viewer


def index() -> rx.Component:
    return map3d_viewer(height="100vh")


app = rx.App()
app.add_page(index)
```

That gives you the upstream map3d experience: draw a box, download the area,
orbit the city, export GLB.

## The three components

| Component | Factory | What it does |
| --- | --- | --- |
| `Map3dAreaSelector` | `map3d_area_selector` | Leaflet map, drag-to-select a bounding box |
| `Map3dScene` | `map3d_scene` | The react-three-fiber city: buildings, roads, export |
| `Map3dViewer` | `map3d_viewer` | Both of the above plus the step-by-step shell |

Use the viewer when you want the finished product; use the selector and the
scene separately when the data should live in your Reflex state.

## Composing the pieces

The interesting pattern: the bounding box goes to the backend, Python queries
Overpass, and the buildings come back as ordinary state. Nothing in the browser
talks to Overpass, so you can cache, filter, enrich or persist the data first.

```python
from typing import Any

import reflex as rx
from reflex_map3d import fetch_buildings_async, map3d_area_selector, map3d_scene


class State(rx.State):
    bbox: dict[str, float] | None = None
    buildings: list[dict[str, Any]] = []
    export_trigger: int = 0

    @rx.event
    def select(self, bbox: dict[str, float]):
        self.bbox = bbox

    @rx.event(background=True)
    async def load(self):
        async with self:
            area = self.bbox
        if not area:
            return
        found = await fetch_buildings_async(area)
        async with self:
            self.buildings = found

    @rx.event
    def export_glb(self):
        self.export_trigger += 1


def index() -> rx.Component:
    return rx.vstack(
        map3d_area_selector(on_select=State.select, height="400px"),
        rx.hstack(
            rx.button("Load", on_click=State.load),
            rx.button("Export GLB", on_click=State.export_glb),
        ),
        map3d_scene(
            bbox=State.bbox,
            buildings=State.buildings,
            export_trigger=State.export_trigger,
            height="600px",
        ),
    )
```

### Letting the browser fetch instead

If you would rather not proxy the data through Python, set `auto_fetch`:

```python
map3d_scene(
    bbox={"north": 40.762, "south": 40.750, "east": -73.974, "west": -73.988},
    auto_fetch=True,
    fetch_roads_from_overpass=True,
    height="600px",
)
```

## Data shapes

A **bounding box** is always `{"north": float, "south": float, "east": float, "west": float}`.

A **building** or **road** is:

```python
{
    "id": 12345,
    "type": "way",
    "tags": {"building": "yes", "height": "31", "name": "…"},
    "geometry": [{"lat": 40.7581, "lng": -73.9855}, ...],
}
```

Anything matching that shape renders — the geometry does not have to come from
OpenStreetMap. Building height is read from the `height` tag, or from
`building:levels` × `level_height`, falling back to `default_height`.

## Python helpers

```python
from reflex_map3d import (
    BBox,                    # normalised bounding box with .center, .span, .to_dict()
    to_bbox,                 # coerce any bbox-ish value into a BBox
    buildings_query,         # the Overpass QL, if you want to run it yourself
    roads_query,
    fetch_buildings,         # blocking
    fetch_roads,
    fetch_buildings_async,   # for @rx.event(background=True)
    fetch_roads_async,
    to_features,             # raw Overpass elements -> the render shape
    OverpassError,           # raised when every endpoint refuses
)
```

Requests are POSTed with the query in the `data` form field, as the Overpass API
documents — sending it as a raw body is what earns a `406 Not Acceptable` from
the public endpoint. When that endpoint rate-limits (`429`) or times out
(`504`), the call falls through to `FALLBACK_OVERPASS_URLS` before giving up.
Set `overpass_url` to your own instance and no mirror is tried.

`BBox.span` is the `dlat + dlng` heuristic map3d uses to warn about large areas
(it warns above `0.1`). Overpass is a shared free service — keep areas small,
cache what you fetch, and consider pointing `overpass_url` at your own instance
for anything beyond a demo.

## Props

### `map3d_area_selector`

| Prop | Type | Default | Notes |
| --- | --- | --- | --- |
| `center` | `list[float]` | `[40.8, -73.95]` | `[lat, lng]` the map opens at |
| `zoom` | `int` | `13` | |
| `tile_url` | `str` | OSM raster tiles | Any XYZ template |
| `attribution` | `str` | OSM attribution | Keep it when using OSM tiles |
| `min_zoom` / `max_zoom` | `int` | `2` / `19` | |
| `rectangle_color` | `str` | `"#1f6feb"` | Selection stroke |
| `show_controls` | `bool` | `True` | The built-in mode/clear buttons |
| `select_label` / `drag_label` / `clear_label` | `str` | English labels | For translated UIs |

Events: `on_select(bbox)`, `on_clear()`, `on_mode_change(drag_enabled)`.

### `map3d_scene`

| Prop | Type | Default | Notes |
| --- | --- | --- | --- |
| `bbox` | `dict` | `None` | The area the projection is centred on |
| `buildings` / `roads` | `list[dict]` | `[]` | Features to render |
| `auto_fetch` | `bool` | `False` | Fetch buildings in the browser |
| `fetch_roads_from_overpass` | `bool` | `False` | Fetch roads in the browser |
| `overpass_url` / `overpass_timeout` | `str` / `int` | public endpoint / `25` | |
| `scale` | `int` | `51000` | World units per degree of latitude |
| `default_height` / `level_height` | `float` | `10.0` / `2.2` | Metres |
| `building_color` / `highlight_color` | `str` | `"#9da0a3"` / `"#007bff"` | |
| `road_color` / `road_width` / `road_elevation` | | `"#34f516"` / `1.0` / `0.1` | |
| `show_roads` / `show_tooltip` / `show_sky` / `show_environment` | `bool` | `True` | |
| `environment_preset` | `str` | `"city"` | drei preset name |
| `background` | `str` | `None` | Solid canvas colour |
| `orbit_controls` | `bool` | `True` | |
| `drive_mode` / `drive_speed` / `drive_color` | | `False` / `3.0` / `"orange"` | WASD driving |
| `camera_fov` / `camera_near` / `camera_far` / `camera_position` | | `90` / `0.1` / `7000` / `[0, 120, 260]` | |
| `auto_frame` | `bool` | `True` | Pull the camera back to fit the area |
| `ambient_intensity` | `float` | `π/2` | |
| `export_trigger` | `int` | `0` | **Increment** it to export a GLB |
| `export_filename` | `str` | `"scene.glb"` | |

Events: `on_building_click(info)`, `on_building_hover(info)`, `on_export(info)`,
`on_load(info)`, `on_error(message)`.

### `map3d_viewer`

Takes the selector props (`center`, `zoom`, `tile_url`, `attribution`), most of
the scene's styling props, plus `include_roads`, `max_span`, `title` and
`description`. Events: `on_select`, `on_load`, `on_export`, `on_step_change`,
`on_building_click`, `on_error`.

## Exporting GLB

Export is edge-triggered: bump `export_trigger` and the browser downloads a
binary GLB of everything in the scene. `on_export` then fires with
`{"filename": ..., "bytes": ...}`. The file never round-trips through the
backend, so large cities do not cost you any server bandwidth.

## Notes and caveats

* **Data accuracy.** Straight from upstream: OpenStreetMap height values are
  often missing or wrong, so buildings fall back to `default_height`. Treat the
  output as an approximation, not a survey.
* **Sizing.** Every component fills its container, so give it a height
  (`height="600px"`, `height="100vh"`, …). `create()` applies a sensible default
  if you forget.
* **The drei environment map** (`show_environment=True`) streams an HDR file
  from a CDN. Behind a firewall or a strict CSP that fetch fails; the scene
  catches it and renders without image-based lighting rather than blanking out.
  Set `show_environment=False` to skip it entirely.
* **Server-side rendering.** All three components are `NoSSRComponent`s — three.js
  and Leaflet both touch `window` on import — so they mount on the client only.
* **Rate limits.** The public Overpass endpoint throttles aggressively. Cache.

## Demo app

```bash
cd map3d_demo
uv pip install -r requirements.txt
uv run reflex run
```

Four pages: the composed selector + backend fetch, the all-in-one viewer, preset
city bounding boxes, and an offline page that renders synthetic geometry with no
network at all.

## Credits

* Upstream project: [cartesiancs/map3d](https://github.com/cartesiancs/map3d) by
  [Hyeong Jun Huh](https://github.com/DipokalLab), MIT licensed.
* Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL.

## License

MIT
