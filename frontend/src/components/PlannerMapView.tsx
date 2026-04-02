import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { getActiveSessions, type ActiveSession } from "../api/client";
import { formatDuration, formatDistance } from "../utils/format";
import "leaflet/dist/leaflet.css";

// Distinct colors for bikers
const BIKER_COLORS = [
  "#6366f1", // indigo
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
];

function getColor(index: number): string {
  return BIKER_COLORS[index % BIKER_COLORS.length];
}

interface PlannerMapViewProps {
  onBack: () => void;
  onViewSession: (sessionId: string) => void;
}

export function PlannerMapView({ onBack, onViewSession }: PlannerMapViewProps) {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    getActiveSessions()
      .then((data) => {
        if (!cancelled) setSessions(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [refreshKey]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Build color map: owner_id -> color
  const colorMap = new Map<number, string>();
  const ownerNames = new Map<number, string>();
  let colorIdx = 0;
  for (const s of sessions) {
    if (s.owner_id && !colorMap.has(s.owner_id)) {
      colorMap.set(s.owner_id, getColor(colorIdx++));
      ownerNames.set(s.owner_id, s.owner_name ?? "Unknown");
    }
  }

  if (loading) {
    return (
      <div className="planner-map-loading">
        <span className="upload-spinner" />
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="planner-map-empty">
        <p>No active routes right now.</p>
        <button className="btn btn-ghost" onClick={onBack}>Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="planner-map-view">
      <div className="planner-map-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Dashboard
        </button>
        <h3>Live Routes ({sessions.length} active)</h3>
        <button className="btn btn-ghost btn-sm" onClick={refresh}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
      </div>

      <div className="planner-map-container">
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
          <FitAllBounds sessions={sessions} />

          {sessions.map((session) => {
            const color = session.owner_id ? colorMap.get(session.owner_id) ?? "#6366f1" : "#6366f1";
            return (
              <SessionLayer key={session.id} session={session} color={color} onViewSession={onViewSession} />
            );
          })}
        </MapContainer>

        {/* Legend */}
        <div className="planner-map-legend">
          {Array.from(ownerNames.entries()).map(([ownerId, name]) => {
            const color = colorMap.get(ownerId)!;
            const bikerSessions = sessions.filter((s) => s.owner_id === ownerId);
            const totalStops = bikerSessions.reduce((sum, s) => sum + s.stop_count, 0);
            const totalDone = bikerSessions.reduce((sum, s) => sum + s.delivered_count, 0);
            return (
              <div key={ownerId} className="planner-map-legend-item">
                <span className="planner-map-legend-dot" style={{ background: color }} />
                <span className="planner-map-legend-name">{name}</span>
                <span className="planner-map-legend-stats">{totalDone}/{totalStops} stops</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Fits map to all active routes
function FitAllBounds({ sessions }: { sessions: ActiveSession[] }) {
  const map = useMap();
  const prevKey = useRef("");

  useEffect(() => {
    const points: [number, number][] = [];
    for (const s of sessions) {
      for (const stop of s.stops) {
        if (stop.lat != null && stop.lng != null) {
          points.push([stop.lat, stop.lng]);
        }
      }
    }
    if (points.length === 0) return;

    const key = points.map((p) => `${p[0]},${p[1]}`).join("|");
    if (key === prevKey.current) return;
    prevKey.current = key;

    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [60, 60] });
  }, [sessions, map]);

  return null;
}

// Renders a single session's route line, stop markers, and current-stop marker
function SessionLayer({ session, color, onViewSession }: { session: ActiveSession; color: string; onViewSession: (id: string) => void }) {
  const map = useMap();
  const routeLayerRef = useRef<L.GeoJSON | null>(null);

  // Route line
  useEffect(() => {
    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    if (!session.route_geometry) return;

    const layer = L.geoJSON(
      { type: "Feature", geometry: session.route_geometry, properties: {} } as GeoJSON.Feature,
      {
        style: {
          color,
          weight: 4,
          opacity: 0.7,
          lineCap: "round",
          lineJoin: "round",
        },
      }
    );
    layer.addTo(map);
    routeLayerRef.current = layer;

    return () => {
      if (routeLayerRef.current) {
        map.removeLayer(routeLayerRef.current);
      }
    };
  }, [session.route_geometry, color, map]);

  const locatedStops = session.stops.filter((s) => s.lat != null && s.lng != null);
  const currentStop = locatedStops.find((s) => s.sequence_order === session.current_stop_index);

  return (
    <>
      {/* Stop markers — small dots */}
      {locatedStops.map((stop) => {
        const isDone = stop.delivery_status !== "pending";
        const isCurrent = stop.sequence_order === session.current_stop_index;
        if (isCurrent) return null; // rendered separately below

        return (
          <Marker
            key={`${session.id}-${stop.id}`}
            position={[stop.lat!, stop.lng!]}
            icon={createSmallDot(color, isDone)}
          />
        );
      })}

      {/* Current stop — larger pulsing marker with popup */}
      {currentStop && (
        <Marker
          key={`${session.id}-current`}
          position={[currentStop.lat!, currentStop.lng!]}
          icon={createCurrentIcon(color, session.owner_name ?? "?")}
        >
          <Popup>
            <div className="planner-map-popup">
              <strong>{session.owner_name}</strong>
              <span className="planner-map-popup-route">{session.name}</span>
              <span className="planner-map-popup-heading">
                Heading to: {currentStop.name}
              </span>
              <span className="planner-map-popup-progress">
                {session.delivered_count}/{session.stop_count} stops done
              </span>
              {session.total_duration != null && (
                <span className="planner-map-popup-eta">
                  Route: {formatDuration(session.total_duration)} / {formatDistance(session.total_distance ?? 0)}
                </span>
              )}
              <button
                className="planner-map-popup-btn"
                onClick={() => onViewSession(session.id)}
              >
                View Route
              </button>
            </div>
          </Popup>
        </Marker>
      )}
    </>
  );
}

function createSmallDot(color: string, isDone: boolean) {
  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${isDone ? "#94a3b8" : color};
      width: 12px;
      height: 12px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,0.2);
      opacity: ${isDone ? "0.5" : "1"};
    "></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function createCurrentIcon(color: string, bikerName: string) {
  const initial = bikerName.charAt(0).toUpperCase();
  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${color};
      color: white;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      font-family: Inter, sans-serif;
      border: 3px solid white;
      box-shadow: 0 0 0 3px ${color}44, 0 2px 8px rgba(0,0,0,0.3);
      cursor: pointer;
    ">${initial}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}
