import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { DeliveryStop, SessionStatus } from "../types";
import "leaflet/dist/leaflet.css";

interface DepotInfo {
  lat: number;
  lng: number;
  address: string;
}

interface DeliveryMapProps {
  stops: DeliveryStop[];
  routeGeometry: GeoJSON.LineString | null;
  onSelectStop: (id: number) => void;
  depot: DepotInfo | null;
  sessionStatus?: SessionStatus;
  currentStopIndex?: number | null;
}

function createNumberedIcon(num: number, stop: DeliveryStop, isCurrent: boolean) {
  // Delivery status colors take priority when route is active
  let color: string;
  let opacity = "1";
  let size = 30;
  let checkmark = false;

  if (stop.delivery_status === "delivered") {
    color = "#10b981"; // green
    opacity = "0.6";
    size = 22;
    checkmark = true;
  } else if (stop.delivery_status === "not_received") {
    color = "#ef4444"; // red
    opacity = "0.6";
    size = 22;
    checkmark = true;
  } else if (stop.delivery_status === "skipped") {
    color = "#94a3b8"; // gray
    opacity = "0.4";
    size = 22;
    checkmark = true;
  } else if (isCurrent) {
    color = "#6366f1"; // indigo
    size = 36;
  } else if (stop.sequence_order != null) {
    color = "#6366f1";
  } else if (stop.geocode_status === "pending") {
    color = "#94a3b8";
  } else if (stop.geocode_status === "failed") {
    color = "#ef4444";
  } else {
    color = "#10b981";
  }

  const content = checkmark
    ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`
    : `${num}`;

  const border = isCurrent ? `3px solid white; box-shadow: 0 0 0 3px ${color}66, 0 2px 8px rgba(0,0,0,0.3)` : "2.5px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.25)";

  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${color};
      color: white;
      width: ${size}px;
      height: ${size}px;
      border-radius: ${isCurrent ? "50%" : "8px"};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: ${isCurrent ? "14px" : "12px"};
      font-family: Inter, sans-serif;
      border: ${border};
      cursor: pointer;
      opacity: ${opacity};
    ">${content}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const homeIcon = L.divIcon({
  className: "numbered-marker",
  html: `<div style="
    background: #f59e0b;
    color: white;
    width: 34px;
    height: 34px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2.5px solid white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  "><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

function FitBounds({ stops, depot }: { stops: DeliveryStop[]; depot: DepotInfo | null }) {
  const map = useMap();
  const prevKey = useRef("");

  useEffect(() => {
    const points: [number, number][] = stops
      .filter((s) => s.lat != null && s.lng != null)
      .map((s) => [s.lat!, s.lng!]);
    if (depot) points.push([depot.lat, depot.lng]);
    if (points.length === 0) return;

    const key = points.map((p) => `${p[0]},${p[1]}`).join("|");
    if (key === prevKey.current) return;
    prevKey.current = key;

    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [60, 60] });
  }, [stops, depot, map]);

  return null;
}

function RouteLayer({ geometry }: { geometry: GeoJSON.LineString }) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }
    const layer = L.geoJSON(
      { type: "Feature", geometry, properties: {} } as GeoJSON.Feature,
      {
        style: {
          color: "#6366f1",
          weight: 4,
          opacity: 0.8,
          lineCap: "round",
          lineJoin: "round",
        },
      }
    );
    layer.addTo(map);
    layerRef.current = layer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
      }
    };
  }, [geometry, map]);

  return null;
}

export function DeliveryMap({ stops, routeGeometry, onSelectStop, depot, sessionStatus, currentStopIndex }: DeliveryMapProps) {
  const located = stops.filter((s) => s.lat != null && s.lng != null);

  return (
    <MapContainer
      center={[47.4979, 19.0402]}
      zoom={12}
      className="delivery-map"
      zoomControl={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds stops={stops} depot={depot} />
      {depot && (
        <Marker
          position={[depot.lat, depot.lng]}
          icon={homeIcon}
        />
      )}
      {located.map((stop, i) => {
        const isCurrent = sessionStatus === "in_progress" && stop.sequence_order === currentStopIndex;
        return (
          <Marker
            key={stop.id}
            position={[stop.lat!, stop.lng!]}
            icon={createNumberedIcon(
              stop.sequence_order != null ? stop.sequence_order : i + 1,
              stop,
              isCurrent
            )}
            eventHandlers={{
              click: () => onSelectStop(stop.id),
            }}
            zIndexOffset={isCurrent ? 1000 : 0}
          />
        );
      })}
      {routeGeometry && <RouteLayer geometry={routeGeometry} />}
    </MapContainer>
  );
}
