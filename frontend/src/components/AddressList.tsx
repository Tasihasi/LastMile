import type { DeliveryStop } from "../types";

interface AddressListProps {
  stops: DeliveryStop[];
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

export function AddressList({ stops }: AddressListProps) {
  if (stops.length === 0) return null;

  return (
    <div className="address-list">
      <div className="address-list-header">
        <h3>Stops</h3>
        <span className="address-list-count">{stops.length}</span>
      </div>
      <ul>
        {stops.map((stop, i) => (
          <li key={stop.id} className="stop-item">
            <span className={numberClass(stop)}>
              {stop.sequence_order != null ? stop.sequence_order : i + 1}
            </span>
            <div className="stop-info">
              <span className="stop-name">{stop.name}</span>
              {stop.raw_address && (
                <span className="stop-address">{stop.raw_address}</span>
              )}
              {stop.lat != null && stop.lng != null && (
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
          </li>
        ))}
      </ul>
    </div>
  );
}
