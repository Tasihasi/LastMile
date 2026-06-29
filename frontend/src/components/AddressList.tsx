import type { DeliveryStop, DeliveryStopStatus, RouteSegment, SessionStatus } from "../types";
import { formatDistance, formatTime, travelSeconds, formatDuration } from "../utils/format";
import { CopyButton } from "./CopyButton";

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
  sessionStatus?: SessionStatus;
  currentStopIndex?: number | null;
  onMarkStop?: (stopId: number, status: DeliveryStopStatus) => void;
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

function deliveryBadge(ds: DeliveryStopStatus) {
  switch (ds) {
    case "delivered":
      return <span className="delivery-badge delivery-badge--delivered">Delivered</span>;
    case "not_received":
      return <span className="delivery-badge delivery-badge--not-received">Not Received</span>;
    case "skipped":
      return <span className="delivery-badge delivery-badge--skipped">Skipped</span>;
    default:
      return null;
  }
}

export function AddressList({ stops, selectedStopId, onSelectStop, routeSegments, arrivalTimes, speedKmh, depot, sessionStatus, currentStopIndex, onMarkStop }: AddressListProps) {
  if (stops.length === 0) return null;

  const isOptimized = stops.some((s) => s.sequence_order != null);

  // After optimization, show stops in route order so the list matches the
  // numbered markers on the map. Before optimization, preserve upload order.
  const orderedStops = isOptimized
    ? [...stops].sort((a, b) => {
        const ao = a.sequence_order ?? Number.POSITIVE_INFINITY;
        const bo = b.sequence_order ?? Number.POSITIVE_INFINITY;
        if (ao !== bo) return ao - bo;
        return a.id - b.id;
      })
    : stops;
  const isRouteActive = sessionStatus === "in_progress";
  const isRouteFinished = sessionStatus === "finished";
  const completedCount = stops.filter((s) => s.delivery_status !== "pending").length;
  const returnHomeArrival = arrivalTimes?.get(-1) ?? null;
  const showReturnHome = depot && isOptimized && routeSegments;
  const returnSegment = showReturnHome ? routeSegments[routeSegments.length - 1] : null;

  return (
    <div className="address-list">
      <div className="address-list-header">
        <h3>Stops</h3>
        <span className="address-list-count">
          {(isRouteActive || isRouteFinished) ? `${completedCount}/${stops.length}` : stops.length}
        </span>
      </div>
      <ul>
        {orderedStops.map((stop, i) => {
          const isCurrentStop = isRouteActive && stop.sequence_order === currentStopIndex;
          const isCompleted = stop.delivery_status !== "pending";
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
                className={`stop-item ${selectedStopId === stop.id ? "stop-item--active" : ""} ${isCurrentStop ? "stop-item--current" : ""} ${isCompleted ? "stop-item--completed" : ""}`}
                onClick={() => onSelectStop(stop.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter") onSelectStop(stop.id); }}
              >
                <span className={`${numberClass(stop)} ${isCompleted ? "stop-number--done" : ""} ${isCurrentStop ? "stop-number--current" : ""}`}>
                  {isCompleted ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    stop.sequence_order != null ? stop.sequence_order : i + 1
                  )}
                </span>
                <div className="stop-info">
                  <span className="stop-name">
                    {isCurrentStop && <span className="stop-current-label">Next </span>}
                    {stop.name}
                  </span>
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
                  {stop.recipient_phone && (
                    <span className="stop-phone" onClick={(e) => e.stopPropagation()}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                      </svg>
                      <a href={`tel:${stop.recipient_phone}`}>{stop.recipient_phone}</a>
                      <CopyButton text={stop.recipient_phone} ariaLabel="Copy phone number" />
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
                  {isCompleted ? (
                    deliveryBadge(stop.delivery_status)
                  ) : (
                    <span className={statusClass(stop.geocode_status)}>
                      {statusLabel(stop.geocode_status)}
                    </span>
                  )}
                </div>
              </div>
              {/* Action buttons for active route stops */}
              {isRouteActive && isCurrentStop && onMarkStop && (
                <div className="stop-actions">
                  <button className="stop-action-btn stop-action-btn--delivered" onClick={(e) => { e.stopPropagation(); onMarkStop(stop.id, "delivered"); }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                    Delivered
                  </button>
                  <button className="stop-action-btn stop-action-btn--not-received" onClick={(e) => { e.stopPropagation(); onMarkStop(stop.id, "not_received"); }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                    Not Received
                  </button>
                  <button className="stop-action-btn stop-action-btn--skipped" onClick={(e) => { e.stopPropagation(); onMarkStop(stop.id, "skipped"); }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /></svg>
                    Skip
                  </button>
                </div>
              )}
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
