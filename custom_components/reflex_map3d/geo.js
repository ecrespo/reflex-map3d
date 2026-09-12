/**
 * Geographic helpers shared by the reflex-map3d components.
 *
 * The projection is the one used by cartesiancs/map3d: an equirectangular
 * approximation around the centre of the bounding box, scaled so that one
 * degree of latitude is `scale` world units.
 */

export const DEFAULT_SCALE = 51000;

/** Read a latitude out of any of the shapes Overpass / Leaflet produce. */
function readLat(point) {
  if (point == null) return NaN;
  if (Array.isArray(point)) return Number(point[0]);
  if (point.lat !== undefined) return Number(point.lat);
  return NaN;
}

/** Read a longitude out of any of the shapes Overpass / Leaflet produce. */
function readLng(point) {
  if (point == null) return NaN;
  if (Array.isArray(point)) return Number(point[1]);
  if (point.lng !== undefined) return Number(point.lng);
  if (point.lon !== undefined) return Number(point.lon);
  return NaN;
}

/**
 * Normalise every accepted bounding-box shape to {north, south, east, west}.
 *
 * Accepted inputs:
 *   {north, south, east, west}
 *   [{lat, lng}, {lat, lng}]   (the shape map3d's Leaflet selector emits)
 *   [[lat, lng], [lat, lng]]
 */
export function normalizeBBox(bbox) {
  if (!bbox) return null;

  if (Array.isArray(bbox)) {
    if (bbox.length < 2) return null;
    const latA = readLat(bbox[0]);
    const lngA = readLng(bbox[0]);
    const latB = readLat(bbox[1]);
    const lngB = readLng(bbox[1]);
    if ([latA, lngA, latB, lngB].some(Number.isNaN)) return null;
    return {
      north: Math.max(latA, latB),
      south: Math.min(latA, latB),
      east: Math.max(lngA, lngB),
      west: Math.min(lngA, lngB),
    };
  }

  if (typeof bbox === "object") {
    const north = Number(bbox.north);
    const south = Number(bbox.south);
    const east = Number(bbox.east);
    const west = Number(bbox.west);
    if ([north, south, east, west].some(Number.isNaN)) return null;
    return {
      north: Math.max(north, south),
      south: Math.min(north, south),
      east: Math.max(east, west),
      west: Math.min(east, west),
    };
  }

  return null;
}

/** Centre of a bounding box as {lat, lng}. */
export function bboxCenter(bbox) {
  const b = normalizeBBox(bbox);
  if (!b) return null;
  return { lat: (b.north + b.south) / 2, lng: (b.east + b.west) / 2 };
}

/**
 * Rough "size" of a bounding box in degrees (dlat + dlng).
 *
 * This mirrors map3d's own `checkIsBig` heuristic, which warns above 0.1.
 */
export function bboxSpan(bbox) {
  const b = normalizeBBox(bbox);
  if (!b) return 0;
  return Math.abs(b.north - b.south) + Math.abs(b.east - b.west);
}

/** True when a bounding box has a non-zero area. */
export function isUsableBBox(bbox) {
  const b = normalizeBBox(bbox);
  if (!b) return false;
  return b.north !== b.south && b.east !== b.west;
}

/**
 * Build a lat/lng -> [x, y] projector centred on `bbox`.
 *
 * The returned function yields metres-ish units on the XY plane; scene code
 * maps them to three.js world space as (x, height, -y).
 */
export function makeProjector(bbox, scale = DEFAULT_SCALE) {
  const center = bboxCenter(bbox) || { lat: 0, lng: 0 };
  const k = Math.cos((center.lat * Math.PI) / 180);
  const s = Number(scale) || DEFAULT_SCALE;
  return function project(lat, lng) {
    return [(Number(lng) - center.lng) * s * k, (Number(lat) - center.lat) * s];
  };
}

/** Normalise an Overpass `geometry` array to [{lat, lng}, ...]. */
export function normalizeGeometry(geometry) {
  if (!Array.isArray(geometry)) return [];
  const out = [];
  for (const point of geometry) {
    const lat = readLat(point);
    const lng = readLng(point);
    if (Number.isNaN(lat) || Number.isNaN(lng)) continue;
    out.push({ lat, lng });
  }
  return out;
}

/**
 * Derive a building height in metres from its OSM tags.
 *
 * `building:levels` wins over `height` when both are present, matching map3d.
 */
export function buildingHeight(tags, options = {}) {
  const defaultHeight = Number(options.defaultHeight ?? 10);
  const levelHeight = Number(options.levelHeight ?? 2.2);
  const safeTags = tags || {};

  let height = parseFloat(safeTags.height);
  const levels = parseFloat(safeTags["building:levels"]);

  if (Number.isNaN(height)) height = defaultHeight;
  if (!Number.isNaN(levels)) height = levels * levelHeight;
  if (!Number.isFinite(height) || height <= 0) height = defaultHeight;

  return height;
}
