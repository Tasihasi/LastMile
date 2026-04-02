import type { DeliveryStop, RouteSegment } from "../types";
import { formatDuration, formatDistance } from "../utils/format";

interface AddressListProps {
  stops: DeliveryStop[];
  selectedStopId: number | null;
  onSelectStop: (id: number) => void;
  routeSegments: RouteSegment[] | null;
}

function statusLabel(s: DeliveryStop["geocode_status"]) {
  switch (s) {
    case "pending":
      return "Pending";
    case "success":
      return "Geocoded";
    case "failed":
      return "Failed";
    case "skipped":
      return "Has coords";
  }
}

function statusClass(s: DeliveryStop["geocode_status"]) {
  return `stop-status stop-status--${s}`;
}

function numberClass(stop: DeliveryStop) {
  if (stop.sequence_order != null) return "stop-number stop-number--optimized";
  return `stop-number stop-number--${stop.geocode_status}`;
}

export function AddressList({ stops, selectedStopId, onSelectStop, routeSegments }: AddressListProps) {
  if (stops.length === 0) return null;

  return (
    <div className="address-list">
      <div className="address-list-header">
        <h3>Stops</h3>
        <span className="address-list-count">{stops.length}</span>
      </div>
      <ul>
        {stops.map((stop, i) => (
          <li key={stop.id}>
            {/* Segment connector showing travel time */}
            {routeSegments && i > 0 && i <= routeSegments.length && (
              <div className="segment-connector">
                <div className="segment-line" />
                <span className="segment-info">
                  {formatDuration(routeSegments[i - 1].duration)} / {formatDistance(routeSegments[i - 1].distance)}
                </span>
                <div className="segment-line" />
              </div>
            )}
            <div
              className={`stop-item ${selectedStopId === stop.id ? "stop-item--active" : ""}`}
              onClick={() => onSelectStop(stop.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter") onSelectStop(stop.id); }}
            >
              <span className={numberClass(stop)}>
                {stop.sequence_order != null ? stop.sequence_order : i + 1}
              </span>
              <div className="stop-info">
                <span className="stop-name">{stop.name}</span>
                {stop.recipient_name && (
                  <span className="stop-recipient">{stop.recipient_name}</span>
                )}
                {stop.raw_address && (
                  <span className="stop-address">{stop.raw_address}</span>
                )}
                {!stop.raw_address && stop.lat != null && stop.lng != null && (
                  <span className="stop-coords">
                    {stop.lat.toFixed(4)}, {stop.lng.toFixed(4)}
                  </span>
                )}
                {stop.geocode_error && (
                  <span className="stop-error">{stop.geocode_error}</span>
                )}
              </div>
              <span className={statusClass(stop.geocode_status)}>
                {statusLabel(stop.geocode_status)}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
