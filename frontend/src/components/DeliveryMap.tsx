import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { DeliveryStop } from "../types";
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
}

function createNumberedIcon(num: number, stop: DeliveryStop) {
  const isOptimized = stop.sequence_order != null;
  const color = isOptimized
    ? "#6366f1"
    : stop.geocode_status === "pending"
      ? "#94a3b8"
      : stop.geocode_status === "failed"
        ? "#ef4444"
        : "#10b981";

  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${color};
      color: white;
      width: 30px;
      height: 30px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 12px;
      font-family: Inter, sans-serif;
      border: 2.5px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
      cursor: pointer;
    ">${num}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
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

export function DeliveryMap({ stops, routeGeometry, onSelectStop, depot }: DeliveryMapProps) {
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
      {located.map((stop, i) => (
        <Marker
          key={stop.id}
          position={[stop.lat!, stop.lng!]}
          icon={createNumberedIcon(
            stop.sequence_order != null ? stop.sequence_order : i + 1,
            stop
          )}
          eventHandlers={{
            click: () => onSelectStop(stop.id),
          }}
        />
      ))}
      {routeGeometry && <RouteLayer geometry={routeGeometry} />}
    </MapContainer>
  );
}
