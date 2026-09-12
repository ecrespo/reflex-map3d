/**
 * All-in-one map3d workflow for Reflex: pick an area, fetch OpenStreetMap
 * data, explore the generated 3D city and export it as GLB.
 *
 * This is a port of the cartesiancs/map3d application shell, with the Fleet
 * upload integration and the emotion styling dropped in favour of plain
 * inline styles so it drops into any Reflex theme.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Download, Spinner, Warning } from "./icons.jsx";

import { Map3dAreaSelector } from "./area_selector.jsx";
import { Map3dScene } from "./scene.jsx";
import { DEFAULT_OVERPASS_URL, fetchBuildings, fetchRoads } from "./overpass.js";
import { DEFAULT_SCALE, bboxSpan, isUsableBBox, normalizeBBox } from "./geo.js";

const STEPS = ["select", "fetch", "scene"];

const overlayStyle = {
  position: "absolute",
  inset: 0,
  zIndex: 30,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "1.5rem",
  backgroundColor: "rgba(248, 249, 251, 0.92)",
  backdropFilter: "blur(6px)",
};

const cardStyle = {
  width: "min(880px, 100%)",
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};

const titleStyle = { fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "#15161a" };
const descStyle = { fontSize: "0.9rem", color: "#6b6d76", margin: 0, lineHeight: 1.5 };

const barStyle = {
  position: "absolute",
  left: 0,
  right: 0,
  bottom: "1.25rem",
  zIndex: 40,
  display: "flex",
  justifyContent: "center",
  gap: "0.75rem",
  pointerEvents: "none",
};

const actionStyle = {
  pointerEvents: "auto",
  display: "inline-flex",
  alignItems: "center",
  gap: "0.5rem",
  padding: "0.6rem 1.1rem",
  borderRadius: "10px",
  border: "none",
  fontSize: "0.9rem",
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 2px 12px rgba(0,0,0,0.14)",
  transition: "0.2s",
};

const primaryAction = { ...actionStyle, backgroundColor: "#1f6feb", color: "#ffffff" };
const ghostAction = { ...actionStyle, backgroundColor: "#ffffff", color: "#15161a" };
const disabledAction = { opacity: 0.5, cursor: "not-allowed" };

const iconStyle = { width: "16px", height: "16px" };
const spinStyle = { ...iconStyle, animation: "map3d-spin 1s linear infinite" };

const SPIN_KEYFRAMES = "@keyframes map3d-spin { to { transform: rotate(360deg); } }";

function StepDots({ step }) {
  return (
    <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
      {STEPS.map((name, index) => (
        <span
          key={name}
          style={{
            width: index === step ? "22px" : "8px",
            height: "8px",
            borderRadius: "999px",
            backgroundColor: index <= step ? "#1f6feb" : "#d6d8de",
            transition: "0.2s",
          }}
        />
      ))}
    </div>
  );
}

function Summary({ buildings, roads, bbox }) {
  const area = normalizeBBox(bbox);
  const cell = (label, value) => (
    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
      <span style={{ fontSize: "0.72rem", textTransform: "uppercase", color: "#8f9099" }}>
        {label}
      </span>
      <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "#15161a" }}>{value}</span>
    </div>
  );

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
        gap: "1rem",
        padding: "1rem",
        borderRadius: "12px",
        backgroundColor: "#ffffff",
        border: "1px solid #e7e8ed",
      }}
    >
      {cell("Buildings", buildings)}
      {cell("Roads", roads)}
      {cell("North / South", area ? `${area.north.toFixed(4)} / ${area.south.toFixed(4)}` : "—")}
      {cell("East / West", area ? `${area.east.toFixed(4)} / ${area.west.toFixed(4)}` : "—")}
    </div>
  );
}

export function Map3dViewer({
  center = [40.8, -73.95],
  zoom = 13,
  tileUrl,
  attribution,
  overpassUrl = DEFAULT_OVERPASS_URL,
  overpassTimeout = 25,
  includeRoads = true,
  maxSpan = 0.1,
  scale = DEFAULT_SCALE,
  defaultHeight = 10,
  levelHeight = 2.2,
  buildingColor = "#9da0a3",
  highlightColor = "#007bff",
  roadColor = "#34f516",
  roadWidth = 1,
  showTooltip = true,
  showSky = true,
  showEnvironment = true,
  environmentPreset = "city",
  driveMode = false,
  exportFilename = "scene.glb",
  title = "Generate 3D map",
  description = "Draw a box over the map to pick an area, then build it in 3D and export it as GLB.",
  onSelect,
  onLoad,
  onExport,
  onStepChange,
  onBuildingClick,
  onError,
  css,
  style,
  className,
  ...rest
}) {
  const [step, setStep] = useState(0);
  const [bbox, setBbox] = useState(null);
  const [buildings, setBuildings] = useState([]);
  const [roads, setRoads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [warned, setWarned] = useState(false);
  const [error, setError] = useState(null);
  const [exportTrigger, setExportTrigger] = useState(0);

  const ready = isUsableBBox(bbox);
  const tooBig = ready && bboxSpan(bbox) > Number(maxSpan);

  const goTo = useCallback(
    (next) => {
      setStep(next);
      if (onStepChange) onStepChange({ step: next, name: STEPS[next] });
    },
    [onStepChange],
  );

  const handleSelect = useCallback(
    (value) => {
      setBbox(value);
      setBuildings([]);
      setRoads([]);
      setWarned(false);
      setError(null);
      if (onSelect) onSelect(value);
    },
    [onSelect],
  );

  const handleClear = useCallback(() => {
    setBbox(null);
    setBuildings([]);
    setRoads([]);
    setWarned(false);
  }, []);

  const load = useCallback(async () => {
    if (!ready) return;
    setLoading(true);
    setError(null);
    try {
      const options = { url: overpassUrl, timeout: overpassTimeout };
      const loadedBuildings = await fetchBuildings(bbox, options);
      const loadedRoads = includeRoads ? await fetchRoads(bbox, options) : [];
      setBuildings(loadedBuildings);
      setRoads(loadedRoads);
      if (onLoad) {
        onLoad({ buildings: loadedBuildings.length, roads: loadedRoads.length, bbox });
      }
    } catch (err) {
      const message = String((err && err.message) || err);
      setError(message);
      if (onError) onError(message);
    } finally {
      setLoading(false);
    }
  }, [ready, bbox, overpassUrl, overpassTimeout, includeRoads, onLoad, onError]);

  const handleNext = useCallback(async () => {
    if (step === 0) {
      if (tooBig && !warned) {
        setWarned(true);
        return;
      }
      goTo(1);
      return;
    }
    if (step === 1) {
      if (!buildings.length && !loading) {
        await load();
        return;
      }
      goTo(2);
    }
  }, [step, tooBig, warned, goTo, buildings.length, loading, load]);

  const handlePrev = useCallback(() => {
    if (step > 0) goTo(step - 1);
  }, [step, goTo]);

  const nextDisabled = useMemo(() => {
    if (loading) return true;
    if (step === 0) return !ready;
    return false;
  }, [loading, step, ready]);

  // See the note in scene.jsx: sizing comes from the Reflex-generated class.
  const wrapperStyle = {
    position: "relative",
    minHeight: "480px",
    overflow: "hidden",
    ...(css || {}),
    ...(style || {}),
  };

  useEffect(() => {
    if (step === 1 && !buildings.length && !loading && !error) {
      // Nothing to do: the user triggers the fetch with "Next step".
    }
  }, [step, buildings.length, loading, error]);

  return (
    <div className={className} style={wrapperStyle} {...rest}>
      <style>{SPIN_KEYFRAMES}</style>

      <div
        style={{
          position: "absolute",
          top: "1rem",
          left: "1rem",
          zIndex: 45,
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          padding: "0.5rem 0.9rem",
          borderRadius: "999px",
          backgroundColor: "rgba(255,255,255,0.9)",
          backdropFilter: "blur(8px)",
          boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
        }}
      >
        <strong style={{ fontSize: "0.85rem", color: "#15161a" }}>map3d</strong>
        <StepDots step={step} />
      </div>

      <Map3dScene
        bbox={bbox}
        buildings={buildings}
        roads={roads}
        autoFetch={false}
        fetchRoadsFromOverpass={false}
        scale={scale}
        defaultHeight={defaultHeight}
        levelHeight={levelHeight}
        buildingColor={buildingColor}
        highlightColor={highlightColor}
        roadColor={roadColor}
        roadWidth={roadWidth}
        showRoads={includeRoads}
        showTooltip={showTooltip}
        showSky={showSky}
        showEnvironment={showEnvironment}
        environmentPreset={environmentPreset}
        driveMode={driveMode}
        exportTrigger={exportTrigger}
        exportFilename={exportFilename}
        onBuildingClick={onBuildingClick}
        onExport={onExport}
        onError={(message) => {
          setError(message);
          if (onError) onError(message);
        }}
        style={{ position: "absolute", inset: 0 }}
      />

      {step === 0 && (
        <div style={overlayStyle}>
          <div style={cardStyle}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <h2 style={titleStyle}>{title}</h2>
              <p style={descStyle}>{description}</p>
            </div>
            <div
              style={{
                height: "min(62vh, 520px)",
                borderRadius: "12px",
                overflow: "hidden",
                border: "1px solid #e7e8ed",
              }}
            >
              <Map3dAreaSelector
                center={center}
                zoom={zoom}
                tileUrl={tileUrl}
                attribution={attribution}
                onSelect={handleSelect}
                onClear={handleClear}
              />
            </div>
            {tooBig && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: "#9a3412",
                  fontSize: "0.85rem",
                }}
              >
                <Warning style={iconStyle} />
                The selected area is large ({bboxSpan(bbox).toFixed(3)}&deg;). Press
                &ldquo;Next step&rdquo; again to continue anyway.
              </div>
            )}
          </div>
        </div>
      )}

      {step === 1 && (
        <div style={overlayStyle}>
          <div style={cardStyle}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <h2 style={titleStyle}>Processing</h2>
              <p style={descStyle}>
                {buildings.length
                  ? "Data is ready. Press “Next step” to open the 3D scene."
                  : "Press “Next step” to download building and road data from OpenStreetMap."}
              </p>
            </div>
            <Summary buildings={buildings.length} roads={roads.length} bbox={bbox} />
            {loading && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: "#6b6d76",
                  fontSize: "0.9rem",
                }}
              >
                <Spinner style={spinStyle} /> Fetching OpenStreetMap data&hellip;
              </div>
            )}
            {error && (
              <div style={{ color: "#b91c1c", fontSize: "0.85rem" }}>{error}</div>
            )}
          </div>
        </div>
      )}

      <div style={barStyle}>
        {step > 0 && (
          <button type="button" style={ghostAction} onClick={handlePrev}>
            <ChevronLeft style={iconStyle} /> Prev step
          </button>
        )}
        {step < 2 && (
          <button
            type="button"
            style={nextDisabled ? { ...primaryAction, ...disabledAction } : primaryAction}
            disabled={nextDisabled}
            onClick={handleNext}
          >
            {loading ? (
              <>
                <Spinner style={spinStyle} /> Fetching&hellip;
              </>
            ) : (
              <>
                Next step <ChevronRight style={iconStyle} />
              </>
            )}
          </button>
        )}
        {step === 2 && (
          <button
            type="button"
            style={primaryAction}
            onClick={() => setExportTrigger((value) => value + 1)}
          >
            Export GLB <Download style={iconStyle} />
          </button>
        )}
      </div>
    </div>
  );
}

export default Map3dViewer;
