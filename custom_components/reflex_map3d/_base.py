"""Shared plumbing for the reflex-map3d components.

The React side of this package ships as plain ``.js``/``.jsx`` files next to
this module. :func:`rx.asset` symlinks them into the consuming app's
``assets/external/`` tree and hands back a ``$/public/...`` specifier that Vite
compiles, so no npm package has to be published for the port to work.

Every file is registered from *this* module on purpose: shared assets are
grouped by the module that registers them, and the relative imports between
the frontend files only resolve when they all land in the same directory.
"""

from __future__ import annotations

import reflex as rx
from reflex.components.component import NoSSRComponent

__all__ = ["FRONTEND_FILES", "NPM_DEPENDENCIES", "Map3dComponent", "asset_library"]

#: npm packages every map3d component pulls in.
#:
#: The versions track the ones cartesiancs/map3d builds against, bumped to the
#: releases that support the React 19 runtime Reflex ships.
NPM_DEPENDENCIES: list[str] = [
    "three@0.186.0",
    "@react-three/fiber@9.7.0",
    "@react-three/drei@10.7.8",
    "react-leaflet@5.0.0",
    "leaflet@1.9.4",
]

#: The frontend files shipped in the wheel, in dependency order.
FRONTEND_FILES: tuple[str, ...] = (
    "geo.js",
    "overpass.js",
    "icons.jsx",
    "tooltip.jsx",
    "area_selector.jsx",
    "scene.jsx",
    "viewer.jsx",
)


def _register_assets() -> dict[str, str]:
    """Link every frontend file into the app and map it to its import path.

    Returns:
        A mapping of file name to the ``$/public/...`` module specifier.
    """
    return {name: rx.asset(name, shared=True).importable_path for name in FRONTEND_FILES}


_ASSETS = _register_assets()


def asset_library(filename: str) -> str:
    """Resolve a bundled frontend file to an importable module path.

    Args:
        filename: The frontend file name, as listed in :data:`FRONTEND_FILES`.

    Returns:
        The module specifier to use as a component ``library``.

    Raises:
        KeyError: If the file is not one of the shipped frontend files.
    """
    return _ASSETS[filename]


class Map3dComponent(NoSSRComponent):
    """Base class for every map3d component.

    three.js, Leaflet and the Overpass fetches all touch ``window``/``document``
    on mount, so the components are imported dynamically on the client only.
    """

    lib_dependencies: list[str] = NPM_DEPENDENCIES
