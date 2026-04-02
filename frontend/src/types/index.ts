export interface User {
  id: number;
  username: string;
  role: "biker" | "planner";
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface SessionSummary {
  id: string;
  created_at: string;
  owner_name: string | null;
  stop_count: number;
}

export interface SharedRouteResponse {
  id: string;
  session: SessionResponse;
  created_at: string;
}

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
}

export interface SessionResponse {
  id: string;
  created_at: string;
  stops: DeliveryStop[];
  needs_geocoding: boolean;
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
