/**
 * Overpass API access for the reflex-map3d components.
 *
 * These are the same queries cartesiancs/map3d issues, factored out so both
 * the scene and the all-in-one viewer can share them.
 */

import { normalizeBBox, normalizeGeometry } from "./geo.js";

export const DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter";

/** Public mirrors tried when the primary endpoint rate-limits. */
export const FALLBACK_OVERPASS_URLS = [
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
];

const RETRYABLE = new Set([429, 502, 503, 504]);

/** Overpass QL for every building way/relation inside `bbox`. */
export function buildingsQuery(bbox, timeout = 25) {
  const b = normalizeBBox(bbox);
  if (!b) return null;
  const box = `${b.south},${b.west},${b.north},${b.east}`;
  return (
    `[out:json][timeout:${timeout}];` +
    `(way["building"](${box});relation["building"](${box}););` +
    `out body geom;`
  );
}

/** Overpass QL for every highway way inside `bbox`. */
export function roadsQuery(bbox, timeout = 25) {
  const b = normalizeBBox(bbox);
  if (!b) return null;
  const box = `${b.south},${b.west},${b.north},${b.east}`;
  return `[out:json][timeout:${timeout}];(way["highway"](${box}););out body geom;`;
}

function endpoints(url) {
  if (url && url !== DEFAULT_OVERPASS_URL) return [url];
  return [DEFAULT_OVERPASS_URL, ...FALLBACK_OVERPASS_URLS];
}

function describe(status, statusText) {
  if (status === 429) return "rate limited — wait a moment or use your own Overpass instance";
  if (status === 504) return "timed out — try a smaller area";
  return statusText || `status ${status}`;
}

/**
 * POST an Overpass QL query and return the parsed JSON payload.
 *
 * The query travels as the form field `data`, which is what the Overpass API
 * documents; sending it as a raw body is what earns a 406 from the public
 * endpoint. Rate-limited responses fall through to the public mirrors.
 */
export async function runQuery(query, options = {}) {
  let last = null;
  for (const url of endpoints(options.url)) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        body: new URLSearchParams({ data: query }),
        headers: { Accept: "application/json" },
        signal: options.signal,
      });
    } catch (error) {
      if (options.signal && options.signal.aborted) throw error;
      last = new Error(`Overpass request to ${url} failed: ${error.message || error}`);
      continue;
    }
    if (RETRYABLE.has(response.status)) {
      last = new Error(`Overpass ${response.status} from ${url}: ${describe(response.status, response.statusText)}`);
      continue;
    }
    if (!response.ok) {
      throw new Error(`Overpass ${response.status} from ${url}: ${describe(response.status, response.statusText)}`);
    }
    return await response.json();
  }
  throw last || new Error("No Overpass endpoint available.");
}

/** Turn raw Overpass elements into the {id, tags, geometry} shape we render. */
export function toFeatures(elements) {
  if (!Array.isArray(elements)) return [];
  const out = [];
  for (const element of elements) {
    const geometry = normalizeGeometry(element.geometry);
    if (!geometry.length) continue;
    out.push({
      id: element.id,
      type: element.type,
      tags: element.tags || {},
      geometry,
    });
  }
  return out;
}

/** Fetch every building inside `bbox`. */
export async function fetchBuildings(bbox, options = {}) {
  const query = buildingsQuery(bbox, options.timeout ?? 25);
  if (!query) return [];
  const data = await runQuery(query, options);
  return toFeatures(data.elements);
}

/** Fetch every road inside `bbox`. */
export async function fetchRoads(bbox, options = {}) {
  const query = roadsQuery(bbox, options.timeout ?? 25);
  if (!query) return [];
  const data = await runQuery(query, options);
  return toFeatures(data.elements);
}
