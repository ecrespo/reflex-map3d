/**
 * The map3d 3D scene, ported from cartesiancs/map3d for Reflex.
 *
 * Renders extruded OpenStreetMap building footprints and road centre lines
 * inside a react-three-fiber canvas, with an optional drive mode and GLB
 * export. Data can either be handed in as props (fetched by the Reflex
 * backend) or fetched in the browser straight from Overpass.
 */

import React, { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment, Html, Line, OrbitControls, Sky } from "@react-three/drei";
import * as THREE from "three";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";

import {
  DEFAULT_SCALE,
  buildingHeight,
  isUsableBBox,
  makeProjector,
  normalizeBBox,
} from "./geo.js";
import { DEFAULT_OVERPASS_URL, fetchBuildings, fetchRoads } from "./overpass.js";
import { BuildingInfo } from "./tooltip.jsx";

const EXPORT_FLAG = "map3dExport";

/* ------------------------------------------------------------------ */
/* Resilience                                                          */
/* ------------------------------------------------------------------ */

/**
 * Keeps an optional part of the scene from taking the whole canvas down.
 *
 * drei's <Environment> streams an HDR map from a CDN; behind a firewall, an
 * offline machine or a strict CSP that fetch throws, and without a boundary
 * the thrown promise rejection unmounts the entire tree.
 */
class Optional extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    if (this.props.onError) {
      this.props.onError(String((error && error.message) || error));
    }
  }

  render() {
    if (this.state.failed) return null;
    return <Suspense fallback={null}>{this.props.children}</Suspense>;
  }
}

/* ------------------------------------------------------------------ */
/* Buildings                                                           */
/* ------------------------------------------------------------------ */

function Building({
  shape,
  depth,
  tags,
  id,
  color,
  highlightColor,
  showTooltip,
  onClick,
  onHover,
}) {
  const [hovered, setHovered] = useState(false);
  const [clicked, setClicked] = useState(false);
  const [hoverPos, setHoverPos] = useState(null);

  const extrudeSettings = useMemo(
    () => ({ steps: 1, depth, bevelEnabled: false }),
    [depth],
  );

  const active = hovered || clicked;

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      userData={{ [EXPORT_FLAG]: true }}
      onPointerOver={(event) => {
        event.stopPropagation();
        setHovered(true);
        if (onHover) onHover({ id, tags });
      }}
      onPointerOut={(event) => {
        event.stopPropagation();
        setHovered(false);
      }}
      onPointerMove={(event) => {
        event.stopPropagation();
        setHoverPos(event.point.clone());
      }}
      onClick={(event) => {
        event.stopPropagation();
        const next = !clicked;
        setClicked(next);
        if (onClick) onClick({ id, tags, selected: next });
      }}
    >
      <extrudeGeometry args={[shape, extrudeSettings]} />
      <meshStandardMaterial color={active ? highlightColor : color} />
      {showTooltip && active && hoverPos && (
        <Html position={[hoverPos.x, hoverPos.y + depth + 0.5, hoverPos.z]} center>
          <BuildingInfo tags={tags} />
        </Html>
      )}
    </mesh>
  );
}

function Buildings({
  features,
  bbox,
  scale,
  defaultHeight,
  levelHeight,
  color,
  highlightColor,
  showTooltip,
  onClick,
  onHover,
}) {
  const items = useMemo(() => {
    if (!isUsableBBox(bbox)) return [];
    const project = makeProjector(bbox, scale);
    const out = [];

    for (const feature of features || []) {
      const geometry = feature.geometry || [];
      if (geometry.length < 3) continue;

      const points = geometry.map((point) => {
        const [x, y] = project(point.lat, point.lng);
        return new THREE.Vector2(x, y);
      });
      if (!points[0].equals(points[points.length - 1])) points.push(points[0]);

      out.push({
        key: `${feature.id ?? out.length}-${out.length}`,
        id: feature.id,
        shape: new THREE.Shape(points),
        depth: buildingHeight(feature.tags, { defaultHeight, levelHeight }),
        tags: feature.tags || {},
      });
    }
    return out;
  }, [features, bbox, scale, defaultHeight, levelHeight]);

  return (
    <>
      {items.map((item) => (
        <Building
          key={item.key}
          id={item.id}
          shape={item.shape}
          depth={item.depth}
          tags={item.tags}
          color={color}
          highlightColor={highlightColor}
          showTooltip={showTooltip}
          onClick={onClick}
          onHover={onHover}
        />
      ))}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Roads                                                               */
/* ------------------------------------------------------------------ */

function Roads({ features, bbox, scale, color, lineWidth, elevation }) {
  const lines = useMemo(() => {
    if (!isUsableBBox(bbox)) return [];
    const project = makeProjector(bbox, scale);
    const out = [];

    for (const feature of features || []) {
      const geometry = feature.geometry || [];
      if (geometry.length < 2) continue;
      const points = geometry.map((point) => {
        const [x, y] = project(point.lat, point.lng);
        return new THREE.Vector3(x, elevation, -y);
      });
      out.push({ key: `${feature.id ?? out.length}-${out.length}`, points });
    }
    return out;
  }, [features, bbox, scale, elevation]);

  return (
    <>
      {lines.map((line) => (
        <Line
          key={line.key}
          points={line.points}
          color={color}
          lineWidth={lineWidth}
          userData={{ [EXPORT_FLAG]: true }}
        />
      ))}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* GLB export                                                          */
/* ------------------------------------------------------------------ */

function Exporter({ trigger, filename, onExport, onError }) {
  const { scene } = useThree();
  const lastTrigger = useRef(trigger);

  useEffect(() => {
    if (trigger === lastTrigger.current) return;
    lastTrigger.current = trigger;
    if (!trigger) return;

    const root = new THREE.Group();
    scene.traverse((child) => {
      if (child.userData && child.userData[EXPORT_FLAG] === true) {
        root.add(child.clone(true));
      }
    });

    const exporter = new GLTFExporter();
    exporter.parse(
      root,
      (result) => {
        if (!(result instanceof ArrayBuffer)) {
          if (onError) onError("GLB export failed: unexpected exporter result.");
          return;
        }
        const blob = new Blob([result], { type: "model/gltf-binary" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.style.display = "none";
        link.href = url;
        link.download = filename || "scene.glb";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        if (onExport) onExport({ filename: filename || "scene.glb", bytes: blob.size });
      },
      (error) => {
        if (onError) onError(String((error && error.message) || error));
      },
      { binary: true, embedImages: true },
    );
  }, [trigger, filename, scene, onExport, onError]);

  return null;
}

/* ------------------------------------------------------------------ */
/* Drive mode                                                          */
/* ------------------------------------------------------------------ */

function Driver({ enabled, orbitControls, speed, color }) {
  const carRef = useRef(null);
  const { camera } = useThree();
  const keys = useRef({ w: false, s: false, a: false, d: false });
  const velocity = useRef(0);

  const handleKeyDown = useCallback((event) => {
    const key = String(event.key || "").toLowerCase();
    if (key in keys.current) keys.current[key] = true;
  }, []);

  const handleKeyUp = useCallback((event) => {
    const key = String(event.key || "").toLowerCase();
    if (key in keys.current) keys.current[key] = false;
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      keys.current = { w: false, s: false, a: false, d: false };
      velocity.current = 0;
    };
  }, [enabled, handleKeyDown, handleKeyUp]);

  useFrame((state, delta) => {
    const car = carRef.current;
    if (!car || !enabled) return;

    const maxSpeed = Number(speed) || 3;
    const acceleration = maxSpeed * 0.07;
    const deceleration = maxSpeed / 3;

    if (keys.current.w) {
      velocity.current = Math.min(maxSpeed, velocity.current + acceleration * delta);
    } else if (keys.current.s) {
      velocity.current = Math.max(-maxSpeed, velocity.current - acceleration * delta);
    } else if (velocity.current > 0) {
      velocity.current = Math.max(0, velocity.current - deceleration * delta);
    } else if (velocity.current < 0) {
      velocity.current = Math.min(0, velocity.current + deceleration * delta);
    }

    if (keys.current.a) car.rotation.y += 0.02;
    if (keys.current.d) car.rotation.y -= 0.02;

    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(car.quaternion);
    car.position.addScaledVector(forward, velocity.current);

    const offset = new THREE.Vector3(0, 1, 2).applyAxisAngle(
      new THREE.Vector3(0, 1, 0),
      car.rotation.y,
    );
    camera.position.lerp(car.position.clone().add(offset), 0.1);
    camera.lookAt(car.position);
  });

  return (
    <>
      {enabled && (
        <mesh ref={carRef} position={[0, 0.5, 0]}>
          <boxGeometry args={[0.2, 0.2, 0.4]} />
          <meshStandardMaterial color={color} />
        </mesh>
      )}
      {!enabled && orbitControls && <OrbitControls makeDefault />}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Camera framing                                                      */
/* ------------------------------------------------------------------ */

/**
 * Pull the camera back far enough to see the whole selected area.
 *
 * Without this the default camera sits at the origin, inside the city, which
 * reads as an empty scene until the user manages to orbit out.
 */
function Framer({ bbox, scale, enabled, ready }) {
  const camera = useThree((state) => state.camera);
  const controls = useThree((state) => state.controls);
  const key = bbox ? `${bbox.north},${bbox.south},${bbox.east},${bbox.west},${scale}` : "";
  const framed = useRef(null);

  useEffect(() => {
    if (!enabled || !ready || !bbox) return;
    if (framed.current === key) return;
    framed.current = key;

    const project = makeProjector(bbox, scale);
    const [x, y] = project(bbox.north, bbox.east);
    const radius = Math.max(Math.abs(x), Math.abs(y), 1);

    camera.position.set(0, radius * 0.9, radius * 1.35);
    camera.updateProjectionMatrix();
    if (controls) {
      controls.target.set(0, 0, 0);
      controls.update();
    } else {
      camera.lookAt(0, 0, 0);
    }
  }, [enabled, ready, key, camera, controls, bbox, scale]);

  return null;
}

/* ------------------------------------------------------------------ */
/* Scene                                                               */
/* ------------------------------------------------------------------ */

export function Map3dScene({
  bbox = null,
  buildings = [],
  roads = [],
  autoFetch = false,
  fetchRoadsFromOverpass = true,
  overpassUrl = DEFAULT_OVERPASS_URL,
  overpassTimeout = 25,
  scale = DEFAULT_SCALE,
  defaultHeight = 10,
  levelHeight = 2.2,
  buildingColor = "#9da0a3",
  highlightColor = "#007bff",
  roadColor = "#34f516",
  roadWidth = 1,
  roadElevation = 0.1,
  showRoads = true,
  showTooltip = true,
  showSky = true,
  showEnvironment = true,
  environmentPreset = "city",
  background = null,
  orbitControls = true,
  driveMode = false,
  driveSpeed = 3,
  driveColor = "orange",
  cameraFov = 90,
  cameraNear = 0.1,
  cameraFar = 7000,
  cameraPosition = [0, 120, 260],
  autoFrame = true,
  ambientIntensity = Math.PI / 2,
  exportTrigger = 0,
  exportFilename = "scene.glb",
  onBuildingClick,
  onBuildingHover,
  onExport,
  onLoad,
  onError,
  children,
  css,
  style,
  className,
  ...rest
}) {
  const area = useMemo(() => normalizeBBox(bbox), [bbox]);
  const areaKey = area ? `${area.north},${area.south},${area.east},${area.west}` : "";

  const [fetchedBuildings, setFetchedBuildings] = useState([]);
  const [fetchedRoads, setFetchedRoads] = useState([]);

  const givenBuildings = Array.isArray(buildings) ? buildings : [];
  const givenRoads = Array.isArray(roads) ? roads : [];

  const shouldFetchBuildings = autoFetch && givenBuildings.length === 0;
  const shouldFetchRoads = showRoads && fetchRoadsFromOverpass && givenRoads.length === 0;

  useEffect(() => {
    if (!area || !shouldFetchBuildings) {
      setFetchedBuildings([]);
      return undefined;
    }
    const controller = new AbortController();
    fetchBuildings(area, { url: overpassUrl, timeout: overpassTimeout, signal: controller.signal })
      .then(setFetchedBuildings)
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (onError) onError(String((error && error.message) || error));
      });
    return () => controller.abort();
  }, [areaKey, shouldFetchBuildings, overpassUrl, overpassTimeout]);

  useEffect(() => {
    if (!area || !shouldFetchRoads) {
      setFetchedRoads([]);
      return undefined;
    }
    const controller = new AbortController();
    fetchRoads(area, { url: overpassUrl, timeout: overpassTimeout, signal: controller.signal })
      .then(setFetchedRoads)
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (onError) onError(String((error && error.message) || error));
      });
    return () => controller.abort();
  }, [areaKey, shouldFetchRoads, overpassUrl, overpassTimeout]);

  const buildingFeatures = givenBuildings.length ? givenBuildings : fetchedBuildings;
  const roadFeatures = givenRoads.length ? givenRoads : fetchedRoads;

  useEffect(() => {
    if (!onLoad) return;
    onLoad({ buildings: buildingFeatures.length, roads: roadFeatures.length });
  }, [buildingFeatures.length, roadFeatures.length]);

  // Reflex hands its style props down as a class (emotion consumes `css`), so
  // the wrapper must not pin its own width/height inline: an inline value would
  // beat the class and collapse the component to its parent's size.
  const wrapperStyle = { position: "relative", ...(css || {}), ...(style || {}) };

  return (
    <div className={className} style={wrapperStyle} {...rest}>
      <Canvas
        camera={{
          fov: cameraFov,
          near: cameraNear,
          far: cameraFar,
          position: cameraPosition,
        }}
      >
        {background && <color attach="background" args={[background]} />}
        <ambientLight intensity={ambientIntensity} />
        <spotLight
          position={[10, 10, 10]}
          angle={0.15}
          penumbra={1}
          decay={0}
          intensity={Math.PI}
        />
        <pointLight position={[-10, -10, -10]} decay={0} intensity={Math.PI} />

        <Suspense fallback={null}>
        <Buildings
          features={buildingFeatures}
          bbox={area}
          scale={scale}
          defaultHeight={defaultHeight}
          levelHeight={levelHeight}
          color={buildingColor}
          highlightColor={highlightColor}
          showTooltip={showTooltip}
          onClick={onBuildingClick}
          onHover={onBuildingHover}
        />

        {showRoads && (
          <Roads
            features={roadFeatures}
            bbox={area}
            scale={scale}
            color={roadColor}
            lineWidth={roadWidth}
            elevation={roadElevation}
          />
        )}

        </Suspense>

        <Framer
          bbox={area}
          scale={scale}
          enabled={autoFrame && !driveMode}
          ready={buildingFeatures.length > 0}
        />

        <Driver
          enabled={driveMode}
          orbitControls={orbitControls}
          speed={driveSpeed}
          color={driveColor}
        />
        <Exporter
          trigger={exportTrigger}
          filename={exportFilename}
          onExport={onExport}
          onError={onError}
        />

        {showSky && (
          <Optional>
            <Sky distance={450000} sunPosition={[0, 1, 0]} inclination={0} azimuth={0.25} />
          </Optional>
        )}
        {showEnvironment && (
          <Optional>
            <Environment preset={environmentPreset} />
          </Optional>
        )}
      </Canvas>
      {children}
    </div>
  );
}

export default Map3dScene;
