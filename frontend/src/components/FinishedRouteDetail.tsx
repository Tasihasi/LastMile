import { useEffect, useState } from "react";
import type { DeliveryStop, SessionResponse } from "../types";
import { getSession } from "../api/client";
import { formatDuration, formatDistance, formatDateTime } from "../utils/format";

interface FinishedRouteDetailProps {
  sessionId: string;
  onClose: () => void;
  onViewMap: (sessionId: string) => void;
}

function elapsedTime(start: string | null, end: string | null): string | null {
  if (!start || !end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms <= 0) return null;
  return formatDuration(Math.round(ms / 1000));
}

function statusIcon(status: DeliveryStop["delivery_status"]) {
  switch (status) {
    case "delivered":
      return (
        <svg className="frd-stop-icon frd-stop-icon--delivered" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      );
    case "not_received":
      return (
        <svg className="frd-stop-icon frd-stop-icon--not-received" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      );
    case "skipped":
      return (
        <svg className="frd-stop-icon frd-stop-icon--skipped" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      );
    default:
      return (
        <svg className="frd-stop-icon frd-stop-icon--pending" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
  }
}

function statusLabel(status: DeliveryStop["delivery_status"]) {
  switch (status) {
    case "delivered": return "Delivered";
    case "not_received": return "Not Received";
    case "skipped": return "Skipped";
    default: return "Pending";
  }
}

export function FinishedRouteDetail({ sessionId, onClose, onViewMap }: FinishedRouteDetailProps) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getSession(sessionId)
      .then((data) => { if (!cancelled) setSession(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (loading) {
    return (
      <div className="frd-overlay" onClick={onClose}>
        <div className="frd-panel" onClick={(e) => e.stopPropagation()}>
          <div className="frd-loading"><span className="upload-spinner" /></div>
        </div>
      </div>
    );
  }

  if (!session) return null;

  const stops = [...session.stops].sort((a, b) => (a.sequence_order ?? 0) - (b.sequence_order ?? 0));
  const delivered = stops.filter((s) => s.delivery_status === "delivered").length;
  const notReceived = stops.filter((s) => s.delivery_status === "not_received").length;
  const skipped = stops.filter((s) => s.delivery_status === "skipped").length;
  const total = stops.length;
  const successRate = total > 0 ? Math.round((delivered / total) * 100) : 0;
  const elapsed = elapsedTime(session.started_at, session.finished_at);

  return (
    <div className="frd-overlay" onClick={onClose}>
      <div className="frd-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="frd-header">
          <div className="frd-header-info">
            <h3>{session.name || "Untitled Route"}</h3>
            <span className="frd-badge frd-badge--finished">Completed</span>
          </div>
          <button className="frd-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Stats grid */}
        <div className="frd-stats">
          <div className="frd-stat">
            <span className="frd-stat-value frd-stat-value--success">{successRate}%</span>
            <span className="frd-stat-label">Success Rate</span>
          </div>
          <div className="frd-stat">
            <span className="frd-stat-value">{delivered}</span>
            <span className="frd-stat-label">Delivered</span>
          </div>
          <div className="frd-stat">
            <span className="frd-stat-value frd-stat-value--danger">{notReceived}</span>
            <span className="frd-stat-label">Not Received</span>
          </div>
          {skipped > 0 && (
            <div className="frd-stat">
              <span className="frd-stat-value frd-stat-value--muted">{skipped}</span>
              <span className="frd-stat-label">Skipped</span>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="frd-timeline">
          <div className="frd-timeline-row">
            <span className="frd-timeline-label">Started</span>
            <span className="frd-timeline-value">{formatDateTime(session.started_at)}</span>
          </div>
          <div className="frd-timeline-row">
            <span className="frd-timeline-label">Finished</span>
            <span className="frd-timeline-value">{formatDateTime(session.finished_at)}</span>
          </div>
          {elapsed && (
            <div className="frd-timeline-row">
              <span className="frd-timeline-label">Duration</span>
              <span className="frd-timeline-value frd-timeline-value--bold">{elapsed}</span>
            </div>
          )}
          {session.total_duration != null && (
            <div className="frd-timeline-row">
              <span className="frd-timeline-label">Route Distance</span>
              <span className="frd-timeline-value">
                {formatDuration(session.total_duration)} / {formatDistance(session.total_distance ?? 0)}
              </span>
            </div>
          )}
        </div>

        {/* Stop list */}
        <div className="frd-stops">
          <div className="frd-stops-header">
            <span>All Stops ({total})</span>
          </div>
          <ul className="frd-stops-list">
            {stops.map((stop) => (
              <li key={stop.id} className={`frd-stop frd-stop--${stop.delivery_status}`}>
                <span className="frd-stop-seq">{stop.sequence_order ?? "—"}</span>
                {statusIcon(stop.delivery_status)}
                <div className="frd-stop-info">
                  <span className="frd-stop-name">{stop.name}</span>
                  {stop.recipient_name && <span className="frd-stop-recipient">{stop.recipient_name}</span>}
                  {stop.raw_address && <span className="frd-stop-address">{stop.raw_address}</span>}
                </div>
                <span className={`frd-stop-status frd-stop-status--${stop.delivery_status}`}>
                  {statusLabel(stop.delivery_status)}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Actions */}
        <div className="frd-actions">
          <button className="btn btn-ghost" onClick={() => onViewMap(sessionId)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            View on Map
          </button>
        </div>
      </div>
    </div>
  );
}
