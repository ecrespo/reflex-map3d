"""Shared data types for reflex-map3d."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

__all__ = ["BBox", "Feature", "to_bbox"]


@dataclasses.dataclass(frozen=True)
class BBox:
    """A geographic bounding box in degrees.

    This is the shape every component exchanges with the Reflex backend:
    ``{"north": ..., "south": ..., "east": ..., "west": ...}``.
    """

    north: float
    south: float
    east: float
    west: float

    def __post_init__(self) -> None:
        """Normalise the corners so ``north >= south`` and ``east >= west``."""
        north, south = float(self.north), float(self.south)
        east, west = float(self.east), float(self.west)
        object.__setattr__(self, "north", max(north, south))
        object.__setattr__(self, "south", min(north, south))
        object.__setattr__(self, "east", max(east, west))
        object.__setattr__(self, "west", min(east, west))

    @property
    def center(self) -> tuple[float, float]:
        """The (lat, lng) centre of the box."""
        return ((self.north + self.south) / 2, (self.east + self.west) / 2)

    @property
    def span(self) -> float:
        """Rough size of the box in degrees (dlat + dlng).

        map3d treats anything above ``0.1`` as a large area.
        """
        return abs(self.north - self.south) + abs(self.east - self.west)

    @property
    def is_empty(self) -> bool:
        """Whether the box has no area."""
        return self.north == self.south or self.east == self.west

    def to_dict(self) -> dict[str, float]:
        """Render as the plain dict the frontend components accept."""
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
        }

    def overpass_bbox(self) -> str:
        """Render as the ``south,west,north,east`` string Overpass expects."""
        return f"{self.south},{self.west},{self.north},{self.east}"


#: A building or road as the components exchange it.
Feature = dict[str, Any]


def _read(point: Any, lat_keys: Sequence[str], index: int) -> float:
    if isinstance(point, Mapping):
        for key in lat_keys:
            if key in point:
                return float(point[key])
        msg = f"Point {point!r} has none of {lat_keys}."
        raise ValueError(msg)
    if isinstance(point, Sequence) and not isinstance(point, (str, bytes)):
        return float(point[index])
    msg = f"Cannot read a coordinate out of {point!r}."
    raise ValueError(msg)


def to_bbox(value: Any) -> BBox:
    """Coerce any accepted bounding-box shape into a :class:`BBox`.

    Accepts a :class:`BBox`, a mapping with ``north``/``south``/``east``/``west``,
    or a pair of points given as mappings (``lat``/``lng`` or ``lat``/``lon``)
    or as ``(lat, lng)`` sequences.

    Args:
        value: The bounding box in any accepted shape.

    Returns:
        The normalised bounding box.

    Raises:
        ValueError: If the value cannot be read as a bounding box.
    """
    if isinstance(value, BBox):
        return value

    if isinstance(value, Mapping):
        if {"north", "south", "east", "west"} <= set(value):
            return BBox(
                north=float(value["north"]),
                south=float(value["south"]),
                east=float(value["east"]),
                west=float(value["west"]),
            )
        msg = f"Mapping {value!r} is not a bounding box."
        raise ValueError(msg)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        points = list(value)
        if len(points) < 2:
            msg = f"A bounding box needs two corners, got {value!r}."
            raise ValueError(msg)
        lat_a = _read(points[0], ("lat",), 0)
        lng_a = _read(points[0], ("lng", "lon"), 1)
        lat_b = _read(points[1], ("lat",), 0)
        lng_b = _read(points[1], ("lng", "lon"), 1)
        return BBox(north=lat_a, south=lat_b, east=lng_a, west=lng_b)

    msg = f"Cannot read a bounding box out of {value!r}."
    raise ValueError(msg)
