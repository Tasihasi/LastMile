import { useState, useCallback } from "react";
import type { DeliveryStop, DeliveryStopStatus, RouteSegment, SessionResponse, SessionStatus } from "../types";
import {
  uploadFile as apiUpload,
  updateStopAddress as apiUpdateStopAddress,
  bulkUpdateStops as apiBulkUpdateStops,
  removeStop as apiRemoveStop,
  getSession as apiGetSession,
  geocodeStops as apiGeocode,
  geocodeStatus as apiGeocodeStatus,
  optimizeRoute as apiOptimize,
  startRoute as apiStartRoute,
  updateStopStatus as apiUpdateStopStatus,
  renameSession as apiRenameSession,
} from "../api/client";

export function useDeliveryPlanner() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionName, setSessionName] = useState("");
  const [stops, setStops] = useState<DeliveryStop[]>([]);
  const [needsGeocoding, setNeedsGeocoding] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [geocodeProgress, setGeocodeProgress] = useState<string>("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [routeGeometry, setRouteGeometry] = useState<GeoJSON.LineString | null>(
    null
  );
  const [routeSegments, setRouteSegments] = useState<RouteSegment[] | null>(null);
  const [totalDuration, setTotalDuration] = useState<number | null>(null);
  const [totalDistance, setTotalDistance] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("not_started");
  const [currentStopIndex, setCurrentStopIndex] = useState<number | null>(null);

  /** Resolves true when the files were imported into the session. */
  const uploadFile = useCallback(async (
    files: File | File[],
    ownerId?: number,
    replaceSessionId?: string | null
  ): Promise<boolean> => {
    setIsUploading(true);
    setError(null);
    try {
      const session: SessionResponse = await apiUpload(files, ownerId, replaceSessionId);
      setSessionId(session.id);
      setSessionName(session.name);
      setStops(session.stops);
      setNeedsGeocoding(session.needs_geocoding);
      setSessionStatus(session.status);
      setCurrentStopIndex(session.current_stop_index);
      setRouteGeometry(null);
      setRouteSegments(null);
      setTotalDuration(null);
      setTotalDistance(null);
      return true;
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { error?: string } } };
        setError(axiosErr.response?.data?.error || "Upload failed.");
      } else {
        setError("Upload failed.");
      }
      return false;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const loadSession = useCallback(async (id: string) => {
    setError(null);
    try {
      const session = await apiGetSession(id);
      setSessionId(session.id);
      setSessionName(session.name);
      setStops(session.stops);
      setNeedsGeocoding(session.needs_geocoding);
      setSessionStatus(session.status);
      setCurrentStopIndex(session.current_stop_index);
      setRouteGeometry(session.route_geometry ?? null);
      setRouteSegments(session.route_segments ?? null);
      setTotalDuration(session.total_duration ?? null);
      setTotalDistance(session.total_distance ?? null);
      return session;
    } catch {
      setError("Failed to load session.");
      return null;
    }
  }, []);

  const geocode = useCallback(async () => {
    if (!sessionId) return;
    setIsGeocoding(true);
    setError(null);
    setGeocodeProgress("");

    try {
      // The geocode endpoint streams one stop per second (Nominatim's rate
      // limit), so a large route can outlive a single request — a server worker
      // timeout or proxy will cut the stream mid-flight (this is why uploads of
      // a few hundred stops appeared to "stop" partway). Each stop is persisted
      // as it resolves, so we drive the stream in resumable passes: re-open it
      // until the server reports zero pending stops. This handles an arbitrary
      // number of points regardless of any single-connection limit.
      const { pending: grandTotal } = await apiGeocodeStatus(sessionId);
      let done = 0;

      // Safety cap: bounded by the work to do, so a permanently-stuck stop
      // can never spin forever.
      for (let pass = 0; pass <= grandTotal; pass++) {
        let advanced = 0;
        try {
          await apiGeocode(sessionId, ({ stop }) => {
            advanced++;
            done++;
            setGeocodeProgress(`Geocoding ${done}/${grandTotal}...`);
            setStops((prev) => prev.map((s) => (s.id === stop.id ? stop : s)));
          });
        } catch {
          // Stream dropped (e.g. server worker timeout). Progress so far is
          // already saved server-side; fall through to check what remains.
        }

        const status = await apiGeocodeStatus(sessionId);
        if (status.pending === 0) break;
        // No stop resolved this pass yet work remains -> genuine failure
        // (e.g. server/network down), not just a cut-off stream. Stop trying.
        if (advanced === 0) {
          throw new Error("Geocoding stalled with stops still pending.");
        }
      }

      setNeedsGeocoding(false);
      setGeocodeProgress("");
    } catch {
      setError("Geocoding failed. Please try again.");
    } finally {
      setIsGeocoding(false);
    }
  }, [sessionId]);

  /** Rewrite a stop's address and re-geocode it. Resolves true if it now has coordinates. */
  const fixAddress = useCallback(async (stopId: number, address: string): Promise<boolean> => {
    if (!sessionId) return false;
    setError(null);
    try {
      const stop = await apiUpdateStopAddress(sessionId, stopId, address);
      setStops((prev) => prev.map((s) => (s.id === stop.id ? stop : s)));
      return stop.geocode_status === "success";
    } catch {
      setError("Failed to update the address.");
      return false;
    }
  }, [sessionId]);

  /** Include/exclude stops and/or move them to another postal-code group. */
  const updateStops = useCallback(async (
    stopIds: number[],
    patch: { excluded?: boolean; postal_code?: string }
  ) => {
    if (!sessionId || stopIds.length === 0) return;
    setError(null);
    // Apply the change right away so checkboxes respond instantly; the server
    // response (or a rollback on failure) settles the final state.
    const ids = new Set(stopIds);
    const before = new Map<number, DeliveryStop>();
    setStops((prev) => prev.map((s) => {
      if (!ids.has(s.id)) return s;
      before.set(s.id, s);
      return { ...s, ...patch };
    }));
    try {
      const updated = await apiBulkUpdateStops(sessionId, stopIds, patch);
      const byId = new Map(updated.map((s) => [s.id, s]));
      setStops((prev) => prev.map((s) => byId.get(s.id) ?? s));
      // Ordering is invalidated server-side; drop the stale route drawing.
      setRouteGeometry(null);
      setRouteSegments(null);
    } catch {
      setStops((prev) => prev.map((s) => before.get(s.id) ?? s));
      setError("Failed to update the stops.");
    }
  }, [sessionId]);

  const discardStop = useCallback(async (stopId: number) => {
    if (!sessionId) return;
    setError(null);
    try {
      await apiRemoveStop(sessionId, stopId);
      setStops((prev) => prev.filter((s) => s.id !== stopId));
    } catch {
      setError("Failed to remove the stop.");
    }
  }, [sessionId]);

  const optimize = useCallback(async (depot?: { lat: number; lng: number } | null) => {
    if (!sessionId) return;
    setIsOptimizing(true);
    setError(null);

    try {
      const result = await apiOptimize(sessionId, depot);
      // Keep stops that are not part of the route (excluded / not located) so
      // stepping back in the wizard still shows them.
      const optimized = new Map(result.optimized_stops.map((s) => [s.id, s]));
      setStops((prev) => prev.map((s) => optimized.get(s.id) ?? s));
      setRouteGeometry(result.route_geometry);
      setRouteSegments(result.route_segments);
      setTotalDuration(result.total_duration);
      setTotalDistance(result.total_distance);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { error?: string } } };
        setError(axiosErr.response?.data?.error || "Optimization failed.");
      } else {
        setError("Optimization failed.");
      }
    } finally {
      setIsOptimizing(false);
    }
  }, [sessionId]);

  const startDeliveryRoute = useCallback(async () => {
    if (!sessionId) return;
    setError(null);
    try {
      const result = await apiStartRoute(sessionId);
      setSessionStatus(result.status);
      setCurrentStopIndex(result.current_stop_index);
    } catch {
      setError("Failed to start route.");
    }
  }, [sessionId]);

  const markStop = useCallback(async (stopId: number, deliveryStatus: DeliveryStopStatus) => {
    if (!sessionId) return;
    setError(null);
    try {
      const result = await apiUpdateStopStatus(sessionId, stopId, deliveryStatus);
      setStops((prev) => prev.map((s) => (s.id === result.stop.id ? result.stop : s)));
      setSessionStatus(result.session_status as SessionStatus);
      setCurrentStopIndex(result.current_stop_index);
    } catch {
      setError("Failed to update stop.");
    }
  }, [sessionId]);

  const renameCurrent = useCallback(async (name: string): Promise<boolean> => {
    if (!sessionId) return false;
    try {
      const saved = await apiRenameSession(sessionId, name);
      setSessionName(saved.name);
      return true;
    } catch {
      setError("Failed to rename the route.");
      return false;
    }
  }, [sessionId]);

  const reset = useCallback(() => {
    setSessionId(null);
    setSessionName("");
    setStops([]);
    setNeedsGeocoding(false);
    setIsGeocoding(false);
    setGeocodeProgress("");
    setIsOptimizing(false);
    setRouteGeometry(null);
    setRouteSegments(null);
    setTotalDuration(null);
    setTotalDistance(null);
    setSessionStatus("not_started");
    setCurrentStopIndex(null);
    setError(null);
  }, []);

  return {
    sessionId,
    sessionName,
    renameCurrent,
    stops,
    needsGeocoding,
    isUploading,
    isGeocoding,
    geocodeProgress,
    isOptimizing,
    routeGeometry,
    routeSegments,
    totalDuration,
    totalDistance,
    error,
    sessionStatus,
    currentStopIndex,
    uploadFile,
    loadSession,
    geocode,
    fixAddress,
    updateStops,
    discardStop,
    optimize,
    startDeliveryRoute,
    markStop,
    reset,
  };
}
