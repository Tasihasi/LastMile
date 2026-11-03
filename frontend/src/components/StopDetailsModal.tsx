import { useEffect } from "react";
import type { DeliveryStop, DeliveryStopStatus, SessionResponse } from "../types";
import { formatDateTime, formatTime } from "../utils/format";

interface StopDetailsModalProps {
  stop: DeliveryStop;
  route: SessionResponse;
  color: string;
  /** Estimated arrival, when the sub-route has been optimized. */
  eta: Date | null;
  stopCount: number;
  onClose: () => void;
}

const STATUS_LABEL: Record<DeliveryStopStatus, string> = {
  pending: "Not delivered yet",
  delivered: "Delivered",
  not_received: "Not received",
  skipped: "Skipped",
};

/** Overlay on the split-review map: everything known about one stop. */
export function StopDetailsModal({ stop, route, color, eta, stopCount, onClose }: StopDetailsModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const done = stop.delivery_status !== "pending";
  const rows: [string, string | null][] = [
    ["Address", stop.raw_address || null],
    ["Postal code", stop.postal_code || null],
    ["Recipient", stop.recipient_name || null],
    ["Phone", stop.recipient_phone || null],
    ["Product code", stop.product_code || null],
    [
      "Position in route",
      stop.sequence_order != null ? `Stop ${stop.sequence_order} of ${stopCount}` : "Route not optimized yet",
    ],
  ];

  return (
    <div className="move-stop-overlay" onClick={onClose}>
      <div
        className="move-stop-card stop-details-card"
        role="dialog"
        aria-label="Stop details"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{stop.name}</h2>

        <div className="stop-details-carrier">
          <span className="cluster-stop-dot" style={{ background: color }} />
          <span>
            Carried by <b>{route.owner_name ?? "Unassigned"}</b> · {route.name}
          </span>
        </div>

        <div className={`stop-details-status stop-details-status--${stop.delivery_status}`}>
          <strong>{STATUS_LABEL[stop.delivery_status]}</strong>
          {done ? (
            <span>
              {stop.delivered_at ? formatDateTime(stop.delivered_at) : "time not recorded"}
            </span>
          ) : eta ? (
            <span>Estimated arrival {formatTime(eta)}</span>
          ) : (
            <span>No estimated arrival until the route is optimized</span>
          )}
        </div>

        <dl className="stop-details-list">
          {rows.map(([label, value]) =>
            value ? (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ) : null
          )}
        </dl>

        <button className="btn btn-ghost" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
