export interface User {
  id: number;
  username: string;
  role: "biker" | "planner";
}

export interface AuthResponse {
  token: string;
  user: User;
}

export type SessionStatus = "not_started" | "in_progress" | "finished";

export interface SessionSummary {
  id: string;
  name: string;
  created_at: string;
  owner_name: string | null;
  stop_count: number;
  total_duration: number | null;
  total_distance: number | null;
  status: SessionStatus;
  started_at: string | null;
  finished_at: string | null;
  current_stop_index: number | null;
  delivered_count: number;
  not_received_count: number;
  current_stop_name: string | null;
}

export interface SharedRouteResponse {
  id: string;
  session: SessionResponse;
  created_at: string;
}

export type DeliveryStopStatus = "pending" | "delivered" | "not_received" | "skipped";

export interface DeliveryStop {
  id: number;
  name: string;
  raw_address: string;
  product_code: string;
  recipient_name: string;
  recipient_phone: string;
  lat: number | null;
  lng: number | null;
  geocode_status: "pending" | "success" | "failed" | "skipped";
  geocode_error: string;
  sequence_order: number | null;
  delivery_status: DeliveryStopStatus;
}

export interface SessionResponse {
  id: string;
  created_at: string;
  stops: DeliveryStop[];
  needs_geocoding: boolean;
  status: SessionStatus;
  started_at: string | null;
  finished_at: string | null;
  current_stop_index: number | null;
  route_geometry: GeoJSON.LineString | null;
  route_segments: RouteSegment[] | null;
}

export interface RouteSegment {
  from_index: number;
  to_index: number;
  duration: number; // seconds
  distance: number; // meters
}

export interface OptimizeResponse {
  optimized_stops: DeliveryStop[];
  route_geometry: GeoJSON.LineString | null;
  route_segments: RouteSegment[] | null;
  total_duration: number | null; // seconds
  total_distance: number | null; // meters
}
