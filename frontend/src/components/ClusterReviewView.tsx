import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { DeliveryStop, SessionResponse, User } from "../types";
import {
  getSession,
  listSessions,
  listBikers,
  optimizeRoute,
  assignSession,
  moveStop,
  deleteSession,
  unclusterSession,
} from "../api/client";
import { useSettings } from "../hooks/useSettings";
import { useToast } from "../hooks/useToast";
import { formatDuration, formatDistance } from "../utils/format";
import "leaflet/dist/leaflet.css";

const CLUSTER_COLORS = [
  "#6366f1", // indigo
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
  "#f97316", // orange
  "#14b8a6", // teal
];

interface SubRouteData {
  session: SessionResponse;
  color: string;
}

interface ClusterReviewViewProps {
  parentSessionId: string;
  onBack: () => void;
  onViewSession: (sessionId: string) => void;
}

export function ClusterReviewView({
  parentSessionId,
  onBack,
  onViewSession,
}: ClusterReviewViewProps) {
  const [subRoutes, setSubRoutes] = useState<SubRouteData[]>([]);
  const [parentSession, setParentSession] = useState<SessionResponse | null>(null);
  const [bikers, setBikers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRoute, setExpandedRoute] = useState<string | null>(null);
  const [optimizingId, setOptimizingId] = useState<string | null>(null);
  const [optimizeAllRunning, setOptimizeAllRunning] = useState(false);
  const [assignDropdown, setAssignDropdown] = useState<string | null>(null);
  const [selectedStop, setSelectedStop] = useState<{
    stop: DeliveryStop;
    routeId: string;
  } | null>(null);
  const [unclustering, setUnclustering] = useState(false);

  const { settings } = useSettings();
  const { showToast } = useToast();

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [parent, sessionList, bikerList] = await Promise.all([
        getSession(parentSessionId),
        listSessions(),
        listBikers(),
      ]);
      setParentSession(parent);
      setBikers(bikerList);

      // Find child sessions of this parent
      const childIds = sessionList
        .filter((s) => s.parent_id === parentSessionId)
        .map((s) => s.id);

      const childSessions = await Promise.all(
        childIds.map((id) => getSession(id))
      );

      setSubRoutes(
        childSessions.map((session, i) => ({
          session,
          color: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
        }))
      );
    } catch {
      setError("Failed to load cluster data.");
    } finally {
      setLoading(false);
    }
  }, [parentSessionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOptimize = async (routeId: string) => {
    setOptimizingId(routeId);
    try {
      const depot =
        settings.homeLat != null && settings.homeLng != null
          ? { lat: settings.homeLat, lng: settings.homeLng }
          : null;
      await optimizeRoute(routeId, depot);
      // Reload the optimized session
      const updated = await getSession(routeId);
      setSubRoutes((prev) =>
        prev.map((r) =>
          r.session.id === routeId ? { ...r, session: updated } : r
        )
      );
    } catch {
      setError("Optimization failed. Check your ORS API key.");
    } finally {
      setOptimizingId(null);
    }
  };

  const handleOptimizeAll = async () => {
    setOptimizeAllRunning(true);
    const depot =
      settings.homeLat != null && settings.homeLng != null
        ? { lat: settings.homeLat, lng: settings.homeLng }
        : null;
    for (const route of subRoutes) {
      if (route.session.total_duration != null) continue; // already optimized
      setOptimizingId(route.session.id);
      try {
        await optimizeRoute(route.session.id, depot);
        const updated = await getSession(route.session.id);
        setSubRoutes((prev) =>
          prev.map((r) =>
            r.session.id === route.session.id ? { ...r, session: updated } : r
          )
        );
      } catch {
        // continue with remaining routes
      }
    }
    setOptimizingId(null);
    setOptimizeAllRunning(false);
  };

  const handleAssign = async (routeId: string, bikerId: number | null) => {
    try {
      await assignSession(routeId, bikerId);
      const updated = await getSession(routeId);
      setSubRoutes((prev) =>
        prev.map((r) =>
          r.session.id === routeId ? { ...r, session: updated } : r
        )
      );
    } catch {
      // ignore
    }
    setAssignDropdown(null);
  };

  const handleMoveStop = async (
    stopId: number,
    fromRouteId: string,
    toRouteId: string
  ) => {
    try {
      await moveStop(fromRouteId, stopId, toRouteId);
      // Reload both affected sessions
      const [fromUpdated, toUpdated] = await Promise.all([
        getSession(fromRouteId),
        getSession(toRouteId),
      ]);
      setSubRoutes((prev) =>
        prev.map((r) => {
          if (r.session.id === fromRouteId) return { ...r, session: fromUpdated };
          if (r.session.id === toRouteId) return { ...r, session: toUpdated };
          return r;
        })
      );
      setSelectedStop(null);
    } catch {
      setError("Failed to move stop.");
    }
  };

  const handleUncluster = async () => {
    const ok = window.confirm(
      `This will delete all ${subRoutes.length} sub-route${subRoutes.length !== 1 ? "s" : ""} and revert to the original file. Continue?`
    );
    if (!ok) return;
    setUnclustering(true);
    try {
      await unclusterSession(parentSessionId);
      showToast("Split undone — sub-routes deleted");
      onBack();
    } catch {
      setError("Failed to undo split. A sub-route may be in progress.");
      showToast("Failed to undo split", "error");
      setUnclustering(false);
    }
  };

  const handleDeleteRoute = async (routeId: string) => {
    try {
      await deleteSession(routeId);
      setSubRoutes((prev) => prev.filter((r) => r.session.id !== routeId));
      showToast("Route deleted");
    } catch {
      setError("Failed to delete route.");
      showToast("Failed to delete route", "error");
    }
  };

  if (loading) {
    return (
      <div className="cluster-review-loading">
        <span className="upload-spinner" />
      </div>
    );
  }

  if (error && subRoutes.length === 0) {
    return (
      <div className="cluster-review-empty">
        <p>{error}</p>
        <button className="btn btn-ghost" onClick={onBack}>
          Back to Dashboard
        </button>
      </div>
    );
  }

  const totalStops = subRoutes.reduce(
    (sum, r) => sum + r.session.stops.length,
    0
  );
  const optimizedCount = subRoutes.filter(
    (r) => r.session.total_duration != null
  ).length;
  const allOptimized = optimizedCount === subRoutes.length;
  const emptyRoutes = subRoutes.filter((r) => r.session.stops.length === 0).length;
  const parentSkippedStops = parentSession
    ? parentSession.stops.filter((s) => s.geocode_status !== "success").length
    : 0;

  // Build a map of routeId -> color for the stop move popup
  const routeColorMap = new Map(
    subRoutes.map((r) => [r.session.id, r.color])
  );

  return (
    <div className="cluster-review">
      <div className="cluster-review-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Dashboard
        </button>
        <h3>{parentSession?.name || "Cluster Review"}</h3>
        <div className="cluster-review-header-actions">
          {!allOptimized && (
            <button
              className="btn btn-primary btn-sm"
              onClick={handleOptimizeAll}
              disabled={optimizeAllRunning}
            >
              {optimizeAllRunning ? (
                <>
                  <span
                    className="upload-spinner"
                    style={{ width: 14, height: 14, borderWidth: 2 }}
                  />
                  Optimizing...
                </>
              ) : (
                <>Optimize All ({subRoutes.length - optimizedCount} remaining)</>
              )}
            </button>
          )}
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleUncluster}
            disabled={unclustering}
            title="Undo split and return to original session"
          >
            {unclustering ? (
              <span
                className="upload-spinner"
                style={{ width: 14, height: 14, borderWidth: 2 }}
              />
            ) : (
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
            )}
            Undo Split
          </button>
        </div>
      </div>

      {error && (
        <div className="cluster-review-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="cluster-review-layout">
        {/* Sidebar */}
        <aside className="cluster-review-sidebar">
          <div className="cluster-review-summary">
            <div className="cluster-review-stat">
              <span className="cluster-review-stat-value">{totalStops}</span>
              <span className="cluster-review-stat-label">Stops</span>
            </div>
            <div className="cluster-review-stat">
              <span className="cluster-review-stat-value">
                {subRoutes.length}
              </span>
              <span className="cluster-review-stat-label">Routes</span>
            </div>
            <div className="cluster-review-stat">
              <span className="cluster-review-stat-value">
                {optimizedCount}/{subRoutes.length}
              </span>
              <span className="cluster-review-stat-label">Optimized</span>
            </div>
          </div>

          {(parentSkippedStops > 0 || emptyRoutes > 0) && (
            <div className="cluster-review-warnings">
              {parentSkippedStops > 0 && (
                <span className="cluster-review-warning">
                  {parentSkippedStops} stop{parentSkippedStops !== 1 ? "s" : ""} skipped (not geocoded)
                </span>
              )}
              {emptyRoutes > 0 && (
                <span className="cluster-review-warning cluster-review-warning--empty">
                  {emptyRoutes} empty route{emptyRoutes !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}

          <div className="cluster-review-routes">
            {subRoutes.map((route) => {
              const isExpanded = expandedRoute === route.session.id;
              const isOptimizing = optimizingId === route.session.id;
              const isOptimized = route.session.total_duration != null;
              const isAssigning = assignDropdown === route.session.id;

              return (
                <div
                  key={route.session.id}
                  className={`cluster-route-card ${isExpanded ? "cluster-route-card--expanded" : ""}`}
                >
                  <div
                    className="cluster-route-card-header"
                    onClick={() =>
                      setExpandedRoute(isExpanded ? null : route.session.id)
                    }
                  >
                    <span
                      className="cluster-route-color"
                      style={{ background: route.color }}
                    />
                    <div className="cluster-route-info">
                      <span className="cluster-route-name">
                        {route.session.name}
                      </span>
                      <span className="cluster-route-meta">
                        {route.session.stops.length} stops
                        {isOptimized && route.session.total_duration != null && (
                          <>
                            {" "}
                            &middot; {formatDuration(route.session.total_duration)}{" "}
                            &middot;{" "}
                            {formatDistance(route.session.total_distance ?? 0)}
                          </>
                        )}
                      </span>
                      {route.session.owner_name && (
                        <span className="cluster-route-owner">
                          Assigned to {route.session.owner_name}
                        </span>
                      )}
                    </div>
                    <svg
                      className={`cluster-route-chevron ${isExpanded ? "cluster-route-chevron--open" : ""}`}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>

                  {/* Route actions */}
                  <div className="cluster-route-actions">
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => handleOptimize(route.session.id)}
                      disabled={isOptimizing || optimizeAllRunning}
                      title={isOptimized ? "Re-optimize" : "Optimize"}
                    >
                      {isOptimizing ? (
                        <span
                          className="upload-spinner"
                          style={{ width: 12, height: 12, borderWidth: 2 }}
                        />
                      ) : (
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                      )}
                    </button>
                    <div className="cluster-route-assign-wrap">
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() =>
                          setAssignDropdown(isAssigning ? null : route.session.id)
                        }
                        title="Assign to biker"
                      >
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                          <circle cx="9" cy="7" r="4" />
                          <line x1="19" y1="8" x2="19" y2="14" />
                          <line x1="22" y1="11" x2="16" y2="11" />
                        </svg>
                      </button>
                      {isAssigning && (
                        <>
                          <div
                            className="cluster-assign-overlay"
                            onClick={() => setAssignDropdown(null)}
                          />
                          <div className="cluster-assign-dropdown">
                            {bikers.map((b) => (
                              <button
                                key={b.id}
                                className={`cluster-assign-option ${b.username === route.session.owner_name ? "cluster-assign-option--current" : ""}`}
                                onClick={() =>
                                  handleAssign(route.session.id, b.id)
                                }
                              >
                                {b.username}
                                {b.username === route.session.owner_name &&
                                  " (current)"}
                              </button>
                            ))}
                            {route.session.owner_name && (
                              <button
                                className="cluster-assign-option cluster-assign-option--unassign"
                                onClick={() =>
                                  handleAssign(route.session.id, null)
                                }
                              >
                                Unassign
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => onViewSession(route.session.id)}
                      title="View full route"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                    {route.session.stops.length === 0 && (
                      <button
                        className="btn btn-sm btn-ghost cluster-route-delete"
                        onClick={() => handleDeleteRoute(route.session.id)}
                        title="Delete empty route"
                      >
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    )}
                  </div>

                  {/* Empty route warning */}
                  {route.session.stops.length === 0 && (
                    <div className="cluster-route-empty-warning">
                      No stops — delete or move stops here
                    </div>
                  )}

                  {/* Expanded stop list */}
                  {isExpanded && (
                    <div className="cluster-route-stops">
                      {route.session.stops.map((stop) => (
                        <div
                          key={stop.id}
                          className={`cluster-stop-item ${selectedStop?.stop.id === stop.id ? "cluster-stop-item--selected" : ""}`}
                          onClick={() =>
                            setSelectedStop(
                              selectedStop?.stop.id === stop.id
                                ? null
                                : { stop, routeId: route.session.id }
                            )
                          }
                        >
                          <span
                            className="cluster-stop-dot"
                            style={{ background: route.color }}
                          />
                          <span className="cluster-stop-name">{stop.name}</span>
                          {stop.sequence_order != null && (
                            <span className="cluster-stop-order">
                              #{stop.sequence_order}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>

        {/* Map */}
        <main className="cluster-review-map">
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
            <FitClusterBounds subRoutes={subRoutes} />
            {subRoutes.map((route) => (
              <ClusterMapLayer
                key={route.session.id}
                route={route}
                selectedStop={selectedStop}
                allRoutes={subRoutes}
                onSelectStop={(stop) =>
                  setSelectedStop(
                    selectedStop?.stop.id === stop.id
                      ? null
                      : { stop, routeId: route.session.id }
                  )
                }
                onMoveStop={handleMoveStop}
                routeColorMap={routeColorMap}
              />
            ))}
          </MapContainer>
        </main>
      </div>
    </div>
  );
}

// Fits map bounds to all cluster stops
function FitClusterBounds({ subRoutes }: { subRoutes: SubRouteData[] }) {
  const map = useMap();
  const prevKey = useRef("");

  useEffect(() => {
    const points: [number, number][] = [];
    for (const route of subRoutes) {
      for (const stop of route.session.stops) {
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
  }, [subRoutes, map]);

  return null;
}

// Renders stops and route line for a single cluster
function ClusterMapLayer({
  route,
  selectedStop,
  allRoutes,
  onSelectStop,
  onMoveStop,
  routeColorMap,
}: {
  route: SubRouteData;
  selectedStop: { stop: DeliveryStop; routeId: string } | null;
  allRoutes: SubRouteData[];
  onSelectStop: (stop: DeliveryStop) => void;
  onMoveStop: (stopId: number, fromRouteId: string, toRouteId: string) => void;
  routeColorMap: Map<string, string>;
}) {
  const map = useMap();
  const routeLayerRef = useRef<L.GeoJSON | null>(null);

  // Draw route line if optimized
  useEffect(() => {
    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    if (!route.session.route_geometry) return;

    const layer = L.geoJSON(
      {
        type: "Feature",
        geometry: route.session.route_geometry,
        properties: {},
      } as GeoJSON.Feature,
      {
        style: {
          color: route.color,
          weight: 3,
          opacity: 0.6,
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
  }, [route.session.route_geometry, route.color, map]);

  const locatedStops = route.session.stops.filter(
    (s) => s.lat != null && s.lng != null
  );

  return (
    <>
      {locatedStops.map((stop) => {
        const isSelected =
          selectedStop?.stop.id === stop.id &&
          selectedStop?.routeId === route.session.id;
        const num = stop.sequence_order ?? 0;

        return (
          <ClusterMarker
            key={`${route.session.id}-${stop.id}`}
            stop={stop}
            route={route}
            isSelected={isSelected}
            num={num}
            allRoutes={allRoutes}
            routeColorMap={routeColorMap}
            onSelectStop={onSelectStop}
            onMoveStop={onMoveStop}
          />
        );
      })}
    </>
  );
}

function ClusterMarker({
  stop,
  route,
  isSelected,
  num,
  allRoutes,
  routeColorMap,
  onSelectStop,
  onMoveStop,
}: {
  stop: DeliveryStop;
  route: SubRouteData;
  isSelected: boolean;
  num: number;
  allRoutes: SubRouteData[];
  routeColorMap: Map<string, string>;
  onSelectStop: (stop: DeliveryStop) => void;
  onMoveStop: (stopId: number, fromSessionId: string, toSessionId: string) => void;
}) {
  const markerRef = useRef<L.Marker>(null);

  useEffect(() => {
    if (isSelected && markerRef.current) {
      markerRef.current.openPopup();
    }
  }, [isSelected]);

  return (
    <Marker
      ref={markerRef}
      position={[stop.lat!, stop.lng!]}
      icon={createClusterIcon(num, route.color, isSelected)}
      eventHandlers={{ click: () => onSelectStop(stop) }}
      zIndexOffset={isSelected ? 1000 : 0}
    >
      <Popup>
        <div className="cluster-stop-popup">
          <strong>{stop.name}</strong>
          {stop.raw_address && <span>{stop.raw_address}</span>}
          {stop.product_code && (
            <span className="cluster-stop-popup-code">
              {stop.product_code}
            </span>
          )}
          <div className="cluster-stop-popup-move">
            <span>Move to:</span>
            {allRoutes
              .filter((r) => r.session.id !== route.session.id)
              .map((r) => (
                <button
                  key={r.session.id}
                  className="cluster-stop-popup-move-btn"
                  onClick={() =>
                    onMoveStop(stop.id, route.session.id, r.session.id)
                  }
                >
                  <span
                    className="cluster-stop-dot"
                    style={{
                      background:
                        routeColorMap.get(r.session.id) ?? "#6366f1",
                    }}
                  />
                  {r.session.name}
                </button>
              ))}
          </div>
        </div>
      </Popup>
    </Marker>
  );
}

function createClusterIcon(
  num: number,
  color: string,
  isSelected: boolean
) {
  const size = isSelected ? 32 : 26;
  const border = isSelected
    ? `3px solid white; box-shadow: 0 0 0 3px ${color}66, 0 2px 8px rgba(0,0,0,0.3)`
    : "2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.2)";

  return L.divIcon({
    className: "numbered-marker",
    html: `<div style="
      background: ${color};
      color: white;
      width: ${size}px;
      height: ${size}px;
      border-radius: ${isSelected ? "50%" : "7px"};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: ${isSelected ? "13px" : "11px"};
      font-family: Inter, sans-serif;
      border: ${border};
      cursor: pointer;
    ">${num || ""}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}
