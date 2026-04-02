import { useState, useCallback } from "react";
import type { DeliveryStop, DeliveryStopStatus, RouteSegment, SessionResponse, SessionStatus } from "../types";
import {
  uploadFile as apiUpload,
  getSession as apiGetSession,
  geocodeStops as apiGeocode,
  optimizeRoute as apiOptimize,
  startRoute as apiStartRoute,
  updateStopStatus as apiUpdateStopStatus,
} from "../api/client";

export function useDeliveryPlanner() {
  const [sessionId, setSessionId] = useState<string | null>(null);
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

  const uploadFile = useCallback(async (file: File, ownerId?: number) => {
    setIsUploading(true);
    setError(null);
    try {
      const session: SessionResponse = await apiUpload(file, ownerId);
      setSessionId(session.id);
      setStops(session.stops);
      setNeedsGeocoding(session.needs_geocoding);
      setSessionStatus(session.status);
      setCurrentStopIndex(session.current_stop_index);
      setRouteGeometry(null);
      setRouteSegments(null);
      setTotalDuration(null);
      setTotalDistance(null);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { error?: string } } };
        setError(axiosErr.response?.data?.error || "Upload failed.");
      } else {
        setError("Upload failed.");
      }
    } finally {
      setIsUploading(false);
    }
  }, []);

  const loadSession = useCallback(async (id: string) => {
    setError(null);
    try {
      const session = await apiGetSession(id);
      setSessionId(session.id);
      setStops(session.stops);
      setNeedsGeocoding(session.needs_geocoding);
      setSessionStatus(session.status);
      setCurrentStopIndex(session.current_stop_index);
      setRouteGeometry(null);
      setRouteSegments(null);
      setTotalDuration(null);
      setTotalDistance(null);
    } catch {
      setError("Failed to load session.");
    }
  }, []);

  const geocode = useCallback(async () => {
    if (!sessionId) return;
    setIsGeocoding(true);
    setError(null);
    setGeocodeProgress("");

    try {
      await apiGeocode(sessionId, ({ stop, progress }) => {
        setGeocodeProgress(`Geocoding ${progress.current}/${progress.total}...`);
        setStops((prev) =>
          prev.map((s) => (s.id === stop.id ? stop : s))
        );
      });
      setNeedsGeocoding(false);
      setGeocodeProgress("");
    } catch {
      setError("Geocoding failed. Please try again.");
    } finally {
      setIsGeocoding(false);
    }
  }, [sessionId]);

  const optimize = useCallback(async (depot?: { lat: number; lng: number } | null) => {
    if (!sessionId) return;
    setIsOptimizing(true);
    setError(null);

    try {
      const result = await apiOptimize(sessionId, depot);
      setStops(result.optimized_stops);
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

  const reset = useCallback(() => {
    setSessionId(null);
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
    optimize,
    startDeliveryRoute,
    markStop,
    reset,
  };
}
