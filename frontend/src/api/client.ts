import axios from "axios";
import type {
  AuthResponse,
  ClusterResponse,
  DeliveryStopStatus,
  DistrictsResponse,
  SplitAssignment,
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
  ownerId?: number,
  parentId?: string
): Promise<SessionSummary[]> {
  const params: Record<string, string | number> = {};
  if (ownerId) params.owner_id = ownerId;
  if (parentId) params.parent_id = parentId;
  const { data } = await api.get<SessionSummary[]>("/sessions/", { params });
  return data;
}

/**
 * Upload one or more files as a single route. Passing `replaceSessionId`
 * re-imports into that not-yet-started session instead of creating a new one.
 */
export async function uploadFile(
  files: File | File[],
  ownerId?: number,
  replaceSessionId?: string | null
): Promise<SessionResponse> {
  const formData = new FormData();
  for (const file of Array.isArray(files) ? files : [files]) {
    formData.append("file", file);
  }
  if (ownerId) formData.append("owner_id", String(ownerId));
  if (replaceSessionId) formData.append("session_id", replaceSessionId);
  const { data } = await api.post<SessionResponse>("/upload/", formData);
  return data;
}

/** Rewrite a stop's address and re-geocode it; returns the updated stop. */
export async function updateStopAddress(
  sessionId: string,
  stopId: number,
  address: string
): Promise<import("../types").DeliveryStop> {
  const { data } = await api.patch<import("../types").DeliveryStop>(
    `/sessions/${sessionId}/stops/${stopId}/address/`,
    { address }
  );
  return data;
}

/** Include/exclude stops from the day's plan and/or move them to another postal-code group. */
export async function bulkUpdateStops(
  sessionId: string,
  stopIds: number[],
  patch: { excluded?: boolean; postal_code?: string }
): Promise<import("../types").DeliveryStop[]> {
  const { data } = await api.post<import("../types").DeliveryStop[]>(
    `/sessions/${sessionId}/stops/bulk/`,
    { stop_ids: stopIds, ...patch }
  );
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

export interface GeocodeStatus {
  total: number;
  pending: number;
  success: number;
  failed: number;
}

/** Count how many of a session's stops are still pending/done geocoding. */
export async function geocodeStatus(
  sessionId: string
): Promise<GeocodeStatus> {
  const { data } = await api.get<GeocodeStatus>(
    `/sessions/${sessionId}/geocode-status/`
  );
  return data;
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
  options?: {
    nRoutes?: number;
    maxStopsPerRoute?: number;
    assignments?: SplitAssignment[];
  }
): Promise<ClusterResponse> {
  const body: Record<string, unknown> = {};
  if (options?.nRoutes != null) body.n_routes = options.nRoutes;
  if (options?.maxStopsPerRoute != null)
    body.max_stops_per_route = options.maxStopsPerRoute;
  if (options?.assignments) body.assignments = options.assignments;
  const { data } = await api.post<ClusterResponse>(
    `/sessions/${sessionId}/cluster/`,
    body
  );
  return data;
}

export async function getSessionDistricts(
  sessionId: string
): Promise<DistrictsResponse> {
  const { data } = await api.get<DistrictsResponse>(
    `/sessions/${sessionId}/districts/`
  );
  return data;
}

export async function removeStop(
  sessionId: string,
  stopId: number
): Promise<{ removed_stop_id: number; remaining_stops: number }> {
  const { data } = await api.delete<{
    removed_stop_id: number;
    remaining_stops: number;
  }>(`/sessions/${sessionId}/stops/${stopId}/remove/`);
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
