import { useEffect, useState } from "react";
import type { SessionSummary } from "../types";
import { listSessions } from "../api/client";
import { formatDuration, formatDistance } from "../utils/format";

function statusOrder(s: SessionSummary): number {
  if (s.status === "in_progress") return 0;
  if (s.status === "not_started") return 1;
  return 2; // finished
}

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

      {!loading && sessions.length > 0 && (() => {
        const sorted = [...sessions].sort((a, b) => statusOrder(a) - statusOrder(b));
        const active = sorted.filter((s) => s.status !== "finished");
        const finished = sorted.filter((s) => s.status === "finished");

        return (
          <>
            <ul className="session-list-items">
              {active.map((s) => (
                <li key={s.id}>
                  <button
                    className={`session-list-item ${s.status === "in_progress" ? "session-list-item--active" : ""}`}
                    onClick={() => onSelectSession(s.id)}
                  >
                    <div className="session-list-item-info">
                      <div className="session-list-item-name-row">
                        {s.status === "in_progress" && <span className="session-list-item-dot" />}
                        <span className="session-list-item-name">{s.name || "Untitled Route"}</span>
                      </div>
                      {s.status === "in_progress" && (
                        <span className="session-list-item-status">
                          {s.delivered_count + s.not_received_count}/{s.stop_count} stops done
                        </span>
                      )}
                      {s.status !== "in_progress" && (
                        <span className="session-list-item-date">{formatDate(s.created_at)}</span>
                      )}
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

            {finished.length > 0 && (
              <details className="session-list-finished">
                <summary className="session-list-finished-toggle">
                  Finished routes ({finished.length})
                </summary>
                <ul className="session-list-items session-list-items--finished">
                  {finished.map((s) => (
                    <li key={s.id}>
                      <button
                        className="session-list-item session-list-item--finished"
                        onClick={() => onSelectSession(s.id)}
                      >
                        <div className="session-list-item-info">
                          <span className="session-list-item-name">{s.name || "Untitled Route"}</span>
                          <span className="session-list-item-date">{formatDate(s.created_at)}</span>
                        </div>
                        <span className="session-list-item-count">
                          {s.stop_count} stop{s.stop_count !== 1 ? "s" : ""}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        );
      })()}
    </div>
  );
}
