import { useEffect, useState } from "react";
import type { SessionSummary } from "../types";
import { listSessions } from "../api/client";
import { formatDuration, formatDistance } from "../utils/format";

interface SessionListProps {
  ownerId?: number;
  onSelectSession: (sessionId: string) => void;
  onNewRoute: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
}

export function SessionList({ ownerId, onSelectSession, onNewRoute }: SessionListProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listSessions(ownerId)
      .then((data) => { if (!cancelled) setSessions(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ownerId]);

  return (
    <div className="session-list">
      <div className="session-list-header">
        <h3>Recent Routes</h3>
        <button className="btn btn-primary btn-sm" onClick={onNewRoute}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Route
        </button>
      </div>

      {loading && (
        <div className="session-list-loading">
          <span className="upload-spinner" />
        </div>
      )}

      {!loading && sessions.length === 0 && (
        <div className="session-list-empty">
          <p>No routes yet. Upload a file to get started.</p>
          <button className="btn btn-primary" onClick={onNewRoute}>
            Upload File
          </button>
        </div>
      )}

      {!loading && sessions.length > 0 && (
        <ul className="session-list-items">
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                className="session-list-item"
                onClick={() => onSelectSession(s.id)}
              >
                <div className="session-list-item-info">
                  <span className="session-list-item-name">{s.name || "Untitled Route"}</span>
                  <span className="session-list-item-date">{formatDate(s.created_at)}</span>
                  {s.total_duration != null && (
                    <span className="session-list-item-duration">
                      {formatDuration(s.total_duration)} / {formatDistance(s.total_distance ?? 0)}
                    </span>
                  )}
                </div>
                <span className="session-list-item-count">
                  {s.stop_count} stop{s.stop_count !== 1 ? "s" : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
