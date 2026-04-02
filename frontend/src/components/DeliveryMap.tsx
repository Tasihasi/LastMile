import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { DeliveryStop } from "../types";
import "leaflet/dist/leaflet.css";

interface DeliveryMapProps {
  stops: DeliveryStop[];
  routeGeometry: GeoJSON.LineString | null;
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
      transition: transform 180ms ease;
    ">${num}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function FitBounds({ stops }: { stops: DeliveryStop[] }) {
  const map = useMap();
  const prevLength = useRef(0);

  useEffect(() => {
    const located = stops.filter((s) => s.lat != null && s.lng != null);
    if (located.length === 0) return;
    if (located.length === prevLength.current) return;
    prevLength.current = located.length;

    const bounds = L.latLngBounds(
      located.map((s) => [s.lat!, s.lng!] as [number, number])
    );
    map.fitBounds(bounds, { padding: [60, 60] });
  }, [stops, map]);

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

export function DeliveryMap({ stops, routeGeometry }: DeliveryMapProps) {
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
      <FitBounds stops={stops} />
      {located.map((stop, i) => (
        <Marker
          key={stop.id}
          position={[stop.lat!, stop.lng!]}
          icon={createNumberedIcon(
            stop.sequence_order != null ? stop.sequence_order : i + 1,
            stop
          )}
        >
          <Popup>
            <strong>{stop.name}</strong>
            {stop.raw_address && <span>{stop.raw_address}</span>}
            {stop.product_code && <span className="popup-meta">Code: {stop.product_code}</span>}
            {stop.recipient_name && <span className="popup-meta">To: {stop.recipient_name}</span>}
            {stop.recipient_phone && <span className="popup-meta">Tel: {stop.recipient_phone}</span>}
          </Popup>
        </Marker>
      ))}
      {routeGeometry && <RouteLayer geometry={routeGeometry} />}
    </MapContainer>
  );
}
