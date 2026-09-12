/**
 * Leaflet bounding-box selector, ported from cartesiancs/map3d for Reflex.
 *
 * The user drags a rectangle over an OpenStreetMap tile layer; the selection
 * is reported back as {north, south, east, west} so a Reflex state can drive
 * the 3D scene with it.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Rectangle, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CircleMinus, PointerClick } from "./icons.jsx";

import { normalizeBBox } from "./geo.js";

const DEFAULT_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors';

const iconStyle = { width: "14px", height: "14px" };

/** Wrap a longitude back into [-180, 180) after a world-wrapping drag. */
function wrapLng(latlng) {
  const lng = ((((latlng.lng + 180) % 360) + 360) % 360) - 180;
  return new L.LatLng(latlng.lat, lng);
}

function boundsToBBox(bounds) {
  const ne = bounds.getNorthEast();
  const sw = bounds.getSouthWest();
  return {
    north: ne.lat,
    south: sw.lat,
    east: ne.lng,
    west: sw.lng,
  };
}

function RectangleSelector({ dragEnabled, drawBounds, rectangleColor, onDraw, onDone }) {
  const [firstPoint, setFirstPoint] = useState(null);
  const lastLatLng = useRef(null);

  const emit = useCallback(
    (start, end, done) => {
      const raw = new L.LatLngBounds(start, end);
      const wrapped = new L.LatLngBounds(wrapLng(start), wrapLng(end));
      onDraw(raw);
      if (done) onDone(boundsToBBox(wrapped));
    },
    [onDraw, onDone],
  );

  const map = useMapEvents({
    mousedown(event) {
      if (!dragEnabled) setFirstPoint(event.latlng);
    },
    mousemove(event) {
      if (!firstPoint) return;
      lastLatLng.current = event.latlng;
      emit(firstPoint, event.latlng, false);
    },
    mouseup(event) {
      if (!firstPoint) return;
      emit(firstPoint, event.latlng, true);
      setFirstPoint(null);
    },
  });

  useEffect(() => {
    if (!map) return undefined;
    const container = map.getContainer();

    const touchStart = (event) => {
      if (dragEnabled || event.touches.length === 0) return;
      setFirstPoint(map.mouseEventToLatLng(event.touches[0]));
    };
    const touchMove = (event) => {
      if (!firstPoint || event.touches.length === 0) return;
      const latlng = map.mouseEventToLatLng(event.touches[0]);
      lastLatLng.current = latlng;
      emit(firstPoint, latlng, false);
    };
    const touchEnd = () => {
      if (!firstPoint) return;
      emit(firstPoint, lastLatLng.current || firstPoint, true);
      setFirstPoint(null);
    };

    container.addEventListener("touchstart", touchStart);
    container.addEventListener("touchmove", touchMove);
    container.addEventListener("touchend", touchEnd);
    return () => {
      container.removeEventListener("touchstart", touchStart);
      container.removeEventListener("touchmove", touchMove);
      container.removeEventListener("touchend", touchEnd);
    };
  }, [map, dragEnabled, firstPoint, emit]);

  useEffect(() => {
    if (!map) return;
    if (dragEnabled) map.dragging.enable();
    else map.dragging.disable();
  }, [dragEnabled, map]);

  return drawBounds ? (
    <Rectangle bounds={drawBounds} pathOptions={{ color: rectangleColor }} />
  ) : null;
}

const buttonBase = {
  backdropFilter: "blur(8px)",
  border: "none",
  padding: "0.5rem 1rem",
  borderRadius: "8px",
  cursor: "pointer",
  transition: "0.2s",
  alignItems: "center",
  gap: "0.5rem",
  fontSize: "14px",
};

export function Map3dAreaSelector({
  center = [40.8, -73.95],
  zoom = 13,
  tileUrl = DEFAULT_TILE_URL,
  attribution = DEFAULT_ATTRIBUTION,
  minZoom = 2,
  maxZoom = 19,
  rectangleColor = "#1f6feb",
  showControls = true,
  selectLabel = "Select Box",
  dragLabel = "Back to Drag",
  clearLabel = "Remove Box",
  onSelect,
  onClear,
  onModeChange,
  children,
  css,
  style,
  className,
  ...rest
}) {
  const [dragEnabled, setDragEnabled] = useState(true);
  const [drawBounds, setDrawBounds] = useState(null);
  const [hasSelection, setHasSelection] = useState(false);

  const mapCenter = useMemo(() => {
    if (Array.isArray(center) && center.length >= 2) return [Number(center[0]), Number(center[1])];
    if (center && typeof center === "object") return [Number(center.lat), Number(center.lng)];
    return [40.8, -73.95];
  }, [center]);

  const handleDone = useCallback(
    (bbox) => {
      setHasSelection(true);
      if (onSelect) onSelect(bbox);
    },
    [onSelect],
  );

  const handleToggleDrag = () => {
    const next = !dragEnabled;
    setDragEnabled(next);
    if (onModeChange) onModeChange(next);
  };

  const handleClear = () => {
    setDrawBounds(null);
    setHasSelection(false);
    setDragEnabled(true);
    if (onModeChange) onModeChange(true);
    if (onClear) onClear();
  };

  // Reflex hands its style props down as a class (emotion consumes `css`), so
  // the wrapper must not pin its own width/height inline: an inline value would
  // beat the class and collapse the component to its parent's size.
  const wrapperStyle = { position: "relative", ...(css || {}), ...(style || {}) };

  return (
    <div className={className} style={wrapperStyle} {...rest}>
      {showControls && (
        <div
          style={{
            position: "absolute",
            zIndex: 999,
            right: "1rem",
            top: "1rem",
            display: "flex",
            justifyContent: "flex-end",
            gap: "0.5rem",
          }}
        >
          <button
            type="button"
            onClick={handleClear}
            style={{
              ...buttonBase,
              display: !hasSelection || dragEnabled ? "none" : "flex",
              color: "#ffffff",
              backgroundColor: "#ef4444",
              outline: "#ef4444c2 solid 0.1rem",
            }}
          >
            <CircleMinus style={iconStyle} /> {clearLabel}
          </button>

          <button
            type="button"
            onClick={handleToggleDrag}
            style={{
              ...buttonBase,
              display: "flex",
              color: dragEnabled ? "#ffffff" : "#000000",
              backgroundColor: dragEnabled ? "#007bffe8" : "#ffffffd8",
              outline: dragEnabled
                ? "#086ad4c2 solid 0.1rem"
                : "rgba(240, 240, 244, 0.51) solid 0.1rem",
            }}
          >
            {dragEnabled ? (
              <>
                <PointerClick style={iconStyle} />
                <span>{selectLabel}</span>
              </>
            ) : (
              <span>{dragLabel}</span>
            )}
          </button>
        </div>
      )}

      <MapContainer
        center={mapCenter}
        zoom={zoom}
        minZoom={minZoom}
        maxZoom={maxZoom}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer attribution={attribution} url={tileUrl} />
        <RectangleSelector
          dragEnabled={dragEnabled}
          drawBounds={drawBounds}
          rectangleColor={rectangleColor}
          onDraw={setDrawBounds}
          onDone={handleDone}
        />
      </MapContainer>
      {children}
    </div>
  );
}

export { normalizeBBox };
export default Map3dAreaSelector;
