/** Building information panel rendered as a drei <Html> overlay. */

import React, { useState } from "react";

const PRIMARY_KEYS = ["building", "height", "building:levels", "amenity", "denomination"];
const ADDRESS_KEYS = [
  "addr:street",
  "addr:housenumber",
  "addr:district",
  "addr:city",
  "addr:postcode",
];
const LABELS = {
  building: "Type",
  height: "Height",
  "building:levels": "Levels",
  amenity: "Facility",
  denomination: "Denomination",
};

const panelStyle = {
  color: "#000000",
  backgroundColor: "#ffffffee",
  backdropFilter: "blur(8px)",
  border: "none",
  padding: "14px",
  borderRadius: "10px",
  fontFamily: "system-ui, -apple-system, sans-serif",
  fontSize: "13px",
  width: "220px",
  boxShadow: "0 2px 14px rgba(0, 0, 0, 0.16)",
  pointerEvents: "auto",
};

const rowStyle = { display: "flex", justifyContent: "space-between", margin: "4px 0", gap: "8px" };
const mutedStyle = { fontWeight: 500, color: "#5f6368" };
const sectionStyle = {
  margin: "10px 0 4px",
  borderTop: "1px solid rgba(0, 0, 0, 0.08)",
  paddingTop: "8px",
};
const toggleStyle = {
  ...mutedStyle,
  marginBottom: "4px",
  cursor: "pointer",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

function isExtraKey(key) {
  return (
    !PRIMARY_KEYS.includes(key) &&
    key !== "name" &&
    key !== "source" &&
    !key.startsWith("addr:") &&
    !key.startsWith("name:") &&
    !key.startsWith("alt_name:")
  );
}

function titleize(key) {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");
}

export function BuildingInfo({ tags }) {
  const [showExtra, setShowExtra] = useState(false);
  const [showNames, setShowNames] = useState(false);

  const safeTags = tags || {};
  const entries = Object.entries(safeTags);
  const extras = entries.filter(([key]) => isExtraKey(key));
  const translations = entries.filter(([key]) => key.startsWith("name:"));
  const hasAddress = ADDRESS_KEYS.some((key) => safeTags[key]);
  const title = safeTags.name || "Building Information";

  return (
    <div role="dialog" aria-label={title} style={panelStyle}>
      <div
        style={{
          fontWeight: 600,
          fontSize: "15px",
          borderBottom: safeTags.name ? "1px solid rgba(0, 0, 0, 0.08)" : "none",
          paddingBottom: safeTags.name ? "6px" : 0,
          marginBottom: safeTags.name ? "8px" : "4px",
        }}
      >
        {title}
      </div>

      {PRIMARY_KEYS.map((key) => {
        const value = safeTags[key];
        if (!value) return null;
        if (key === "building" && value === "yes") return null;
        return (
          <div key={key} style={rowStyle}>
            <span style={mutedStyle}>{LABELS[key] || titleize(key)}:</span>
            <span style={{ textTransform: "capitalize" }}>
              {key === "height" ? `${value} m` : value}
            </span>
          </div>
        );
      })}

      {hasAddress && (
        <div style={sectionStyle}>
          <div style={{ ...mutedStyle, marginBottom: "4px" }}>Address</div>
          <div style={{ marginLeft: "4px", fontSize: "12px", color: "#5f6368" }}>
            {[
              [safeTags["addr:street"], safeTags["addr:housenumber"]].filter(Boolean).join(" "),
              safeTags["addr:district"],
              safeTags["addr:city"],
              safeTags["addr:postcode"],
            ]
              .filter(Boolean)
              .join(", ")}
          </div>
        </div>
      )}

      {extras.length > 0 && (
        <div style={sectionStyle}>
          <div style={toggleStyle} onClick={() => setShowExtra(!showExtra)}>
            Additional Information
            <span>{showExtra ? "▲" : "▼"}</span>
          </div>
          {showExtra &&
            extras.map(([key, value]) => {
              const long = key === "description" || String(value).length > 80;
              if (long) {
                return (
                  <div key={key} style={{ margin: "8px 0" }}>
                    <div style={{ ...mutedStyle, marginBottom: "4px" }}>{titleize(key)}</div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#5f6368",
                        whiteSpace: "pre-wrap",
                        lineHeight: 1.4,
                        backgroundColor: "rgba(0,0,0,0.02)",
                        padding: "6px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      {String(value)}
                    </div>
                  </div>
                );
              }
              return (
                <div key={key} style={rowStyle}>
                  <span style={{ ...mutedStyle, fontWeight: 700 }}>{titleize(key)}:</span>
                  <span style={{ textAlign: "right" }}>{String(value)}</span>
                </div>
              );
            })}
        </div>
      )}

      {translations.length > 0 && (
        <div style={sectionStyle}>
          <div style={toggleStyle} onClick={() => setShowNames(!showNames)}>
            Name Translations
            <span>{showNames ? "▲" : "▼"}</span>
          </div>
          {showNames &&
            translations.map(([key, value]) => (
              <div key={key} style={rowStyle}>
                <span style={mutedStyle}>{key.replace("name:", "").toUpperCase()}:</span>
                <span>{String(value)}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default BuildingInfo;
