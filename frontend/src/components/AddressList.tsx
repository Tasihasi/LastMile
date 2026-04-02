import type { DeliveryStop, RouteSegment } from "../types";
import { formatDistance, formatTime, travelSeconds, formatDuration } from "../utils/format";

interface DepotInfo {
  lat: number;
  lng: number;
  address: string;
}

interface AddressListProps {
  stops: DeliveryStop[];
  selectedStopId: number | null;
  onSelectStop: (id: number) => void;
  routeSegments: RouteSegment[] | null;
  arrivalTimes: Map<number, Date> | null;
  speedKmh: number;
  depot: DepotInfo | null;
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

export function AddressList({ stops, selectedStopId, onSelectStop, routeSegments, arrivalTimes, speedKmh, depot }: AddressListProps) {
  if (stops.length === 0) return null;

  const isOptimized = stops.some((s) => s.sequence_order != null);
  const returnHomeArrival = arrivalTimes?.get(-1) ?? null;
  const showReturnHome = depot && isOptimized && routeSegments;
  const returnSegment = showReturnHome ? routeSegments[routeSegments.length - 1] : null;

  return (
    <div className="address-list">
      <div className="address-list-header">
        <h3>Stops</h3>
        <span className="address-list-count">{stops.length}</span>
      </div>
      <ul>
        {stops.map((stop, i) => {
          const arrival = stop.sequence_order != null && arrivalTimes
            ? arrivalTimes.get(stop.sequence_order) ?? null
            : null;

          // When depot is set, segment indices shift: seg[0]=depot->s1, seg[1]=s1->s2, etc.
          const segIndex = depot ? i : i - 1;

          return (
            <li key={stop.id}>
              {/* Segment connector showing travel time */}
              {routeSegments && segIndex >= 0 && segIndex < routeSegments.length && (depot ? true : i > 0) && (
                <div className="segment-connector">
                  <div className="segment-line" />
                  <span className="segment-info">
                    {formatDuration(travelSeconds(routeSegments[segIndex].distance, speedKmh))} / {formatDistance(routeSegments[segIndex].distance)}
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
                <div className="stop-right">
                  {arrival && (
                    <span className="stop-arrival">{formatTime(arrival)}</span>
                  )}
                  <span className={statusClass(stop.geocode_status)}>
                    {statusLabel(stop.geocode_status)}
                  </span>
                </div>
              </div>
            </li>
          );
        })}

        {/* Return home */}
        {showReturnHome && returnSegment && (
          <li>
            <div className="segment-connector">
              <div className="segment-line" />
              <span className="segment-info">
                {formatDuration(travelSeconds(returnSegment.distance, speedKmh))} / {formatDistance(returnSegment.distance)}
              </span>
              <div className="segment-line" />
            </div>
            <div className="stop-item stop-item--home">
              <span className="stop-number stop-number--home">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9 22 9 12 15 12 15 22" />
                </svg>
              </span>
              <div className="stop-info">
                <span className="stop-name">Return Home</span>
                <span className="stop-address">{depot.address}</span>
              </div>
              <div className="stop-right">
                {returnHomeArrival && (
                  <span className="stop-arrival">{formatTime(returnHomeArrival)}</span>
                )}
                <span className="stop-status stop-status--home">Home</span>
              </div>
            </div>
          </li>
        )}
      </ul>
    </div>
  );
}
