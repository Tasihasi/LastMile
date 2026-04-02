export interface DeliveryStop {
  id: number;
  name: string;
  raw_address: string;
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

export interface OptimizeResponse {
  optimized_stops: DeliveryStop[];
  route_geometry: GeoJSON.LineString | null;
}
