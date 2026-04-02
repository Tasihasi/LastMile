import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { DeliveryStop } from "../types";
import "leaflet/dist/leaflet.css";

interface DeliveryMapProps {
  stops: DeliveryStop[];
  routeGeometry: GeoJSON.LineString | null;
}

function createNumberedIcon(num: number, status: DeliveryStop["geocode_status"]) {
  const color =
    status === "pending"
      ? "#9ca3af"
      : status === "failed"
        ? "#ef4444"
        : status === "skipped" || status === "success"
          ? "#22c55e"
          : "#3b82f6";

  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${color};
      color: white;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 13px;
      border: 2px solid white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    ">${num}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
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
    map.fitBounds(bounds, { padding: [50, 50] });
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
        style: { color: "#3b82f6", weight: 4, opacity: 0.7 },
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
            stop.geocode_status
          )}
        >
          <Popup>
            <strong>{stop.name}</strong>
            {stop.raw_address && <br />}
            {stop.raw_address}
          </Popup>
        </Marker>
      ))}
      {routeGeometry && <RouteLayer geometry={routeGeometry} />}
    </MapContainer>
  );
}
