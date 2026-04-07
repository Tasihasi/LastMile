import axios from "axios";
import type {
  AuthResponse,
  ClusterResponse,
  DeliveryStopStatus,
  MoveStopResponse,
  OptimizeResponse,
  SessionResponse,
  SessionSummary,
  SharedRouteResponse,
  User,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const api = axios.create({
  baseURL: API_BASE,
});

// Auth interceptor — attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth-token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// ============================================
// Auth
// ============================================

export async function login(
  username: string,
  role: "biker" | "planner"
): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/login/", {
    username,
    role,
  });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me/");
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout/");
}

// ============================================
// Sessions
// ============================================

export async function listSessions(
  ownerId?: number
): Promise<SessionSummary[]> {
  const params = ownerId ? { owner_id: ownerId } : {};
  const { data } = await api.get<SessionSummary[]>("/sessions/", { params });
  return data;
}

export async function uploadFile(
  file: File,
  ownerId?: number
): Promise<SessionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (ownerId) formData.append("owner_id", String(ownerId));
  const { data } = await api.post<SessionResponse>("/upload/", formData);
  return data;
}

export async function getSession(
  sessionId: string
): Promise<SessionResponse> {
  const { data } = await api.get<SessionResponse>(
    `/sessions/${sessionId}/`
  );
  return data;
}

export async function optimizeRoute(
  sessionId: string,
  depot?: { lat: number; lng: number } | null
): Promise<OptimizeResponse> {
  const body = depot ? { depot_lat: depot.lat, depot_lng: depot.lng } : {};
  const { data } = await api.post<OptimizeResponse>(
    `/sessions/${sessionId}/optimize/`,
    body
  );
  return data;
}

// ============================================
// Geocoding (NDJSON stream)
// ============================================

export interface GeocodeProgress {
  stop: import("../types").DeliveryStop;
  progress: { current: number; total: number };
}

export async function geocodeStops(
  sessionId: string,
  onProgress: (data: GeocodeProgress) => void
): Promise<void> {
  const token = localStorage.getItem("auth-token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Token ${token}`;

  const response = await fetch(
    `${API_BASE}/sessions/${sessionId}/geocode/`,
    { method: "POST", headers }
  );

  if (!response.ok) {
    throw new Error("Geocoding request failed");
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.trim()) {
        const data: GeocodeProgress = JSON.parse(line);
        onProgress(data);
      }
    }
  }

  if (buffer.trim()) {
    const data: GeocodeProgress = JSON.parse(buffer);
    onProgress(data);
  }
}

// ============================================
// Sharing
// ============================================

export async function shareSession(
  sessionId: string
): Promise<string> {
  const { data } = await api.post<{ share_id: string }>(
    `/sessions/${sessionId}/share/`
  );
  return data.share_id;
}

export async function getSharedRoute(
  shareId: string
): Promise<SharedRouteResponse> {
  const { data } = await api.get<SharedRouteResponse>(
    `/shared/${shareId}/`
  );
  return data;
}

// ============================================
// Planner
// ============================================

export async function listBikers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/users/bikers/");
  return data;
}

export async function getActiveSessions(): Promise<ActiveSession[]> {
  const { data } = await api.get<ActiveSession[]>("/sessions/active/");
  return data;
}

export interface ActiveSessionStop {
  id: number;
  name: string;
  lat: number | null;
  lng: number | null;
  sequence_order: number | null;
  delivery_status: import("../types").DeliveryStopStatus;
}

export interface ActiveSession {
  id: string;
  name: string;
  owner_name: string | null;
  owner_id: number | null;
  status: string;
  started_at: string | null;
  current_stop_index: number | null;
  stop_count: number;
  delivered_count: number;
  current_stop_name: string | null;
  total_duration: number | null;
  total_distance: number | null;
  route_geometry: GeoJSON.LineString | null;
  stops: ActiveSessionStop[];
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/sessions/${sessionId}/delete/`);
}

export async function assignSession(
  sessionId: string,
  ownerId: number | null
): Promise<void> {
  await api.patch(`/sessions/${sessionId}/assign/`, {
    owner_id: ownerId,
  });
}

export async function renameSession(
  sessionId: string,
  name: string
): Promise<{ name: string }> {
  const { data } = await api.patch<{ name: string }>(
    `/sessions/${sessionId}/rename/`,
    { name }
  );
  return data;
}

// ============================================
// Clustering
// ============================================

export async function clusterSession(
  sessionId: string,
  nRoutes?: number,
  maxStopsPerRoute?: number
): Promise<ClusterResponse> {
  const body: Record<string, number> = {};
  if (nRoutes != null) body.n_routes = nRoutes;
  if (maxStopsPerRoute != null) body.max_stops_per_route = maxStopsPerRoute;
  const { data } = await api.post<ClusterResponse>(
    `/sessions/${sessionId}/cluster/`,
    body
  );
  return data;
}

export async function moveStop(
  sessionId: string,
  stopId: number,
  toSessionId: string
): Promise<MoveStopResponse> {
  const { data } = await api.post<MoveStopResponse>(
    `/sessions/${sessionId}/move-stop/`,
    { stop_id: stopId, to_session_id: toSessionId }
  );
  return data;
}

export async function unclusterSession(
  sessionId: string
): Promise<{ parent_id: string; deleted_routes: number }> {
  const { data } = await api.delete<{
    parent_id: string;
    deleted_routes: number;
  }>(`/sessions/${sessionId}/uncluster/`);
  return data;
}

// ============================================
// Route Lifecycle
// ============================================

export async function startRoute(
  sessionId: string
): Promise<SessionSummary> {
  const { data } = await api.patch<SessionSummary>(
    `/sessions/${sessionId}/start/`
  );
  return data;
}

export async function updateStopStatus(
  sessionId: string,
  stopId: number,
  status: DeliveryStopStatus
): Promise<{
  stop: import("../types").DeliveryStop;
  session_status: string;
  current_stop_index: number | null;
}> {
  const { data } = await api.patch(
    `/sessions/${sessionId}/stops/${stopId}/status/`,
    { status }
  );
  return data;
}
