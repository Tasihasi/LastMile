import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionSummary, User } from "../types";
import {
  listBikers,
  listSessions,
  deleteSession,
  assignSession,
  uploadFile as apiUpload,
} from "../api/client";

interface PlannerDashboardProps {
  onViewSession: (sessionId: string) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function PlannerDashboard({ onViewSession }: PlannerDashboardProps) {
  const [bikers, setBikers] = useState<User[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignDropdown, setAssignDropdown] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | undefined>();

  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listBikers(), listSessions()])
      .then(([b, s]) => {
        if (cancelled) return;
        setBikers(b);
        setSessions(s);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [refreshKey]);

  const handleDelete = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch { /* ignore */ }
    setConfirmDelete(null);
  };

  const handleAssign = async (sessionId: string, ownerId: number) => {
    try {
      await assignSession(sessionId, ownerId);
      refresh();
    } catch { /* ignore */ }
    setAssignDropdown(null);
  };

  const handleUploadClick = (bikerId?: number) => {
    setUploadTarget(bikerId);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await apiUpload(file, uploadTarget);
      refresh();
    } catch { /* ignore */ }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Group sessions by owner
  const unassigned = sessions.filter((s) => !s.owner_name);
  const bikerSessions = new Map<string, SessionSummary[]>();
  for (const biker of bikers) {
    bikerSessions.set(
      biker.username,
      sessions.filter((s) => s.owner_name === biker.username)
    );
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        <span className="upload-spinner" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.txt,.xml"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <div className="dashboard-header">
        <h2>Route Management</h2>
        <button className="btn btn-primary btn-sm" onClick={() => handleUploadClick()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Upload Route
        </button>
      </div>

      <div className="dashboard-grid">
        {/* Unassigned column */}
        {unassigned.length > 0 && (
          <div className="dashboard-column">
            <div className="dashboard-column-header">
              <span className="dashboard-column-title">Unassigned</span>
              <span className="dashboard-column-count">{unassigned.length}</span>
            </div>
            <div className="dashboard-column-cards">
              {unassigned.map((s) => (
                <SessionCard
                  key={s.id}
                  session={s}
                  bikers={bikers}
                  assignDropdown={assignDropdown}
                  confirmDelete={confirmDelete}
                  onView={() => onViewSession(s.id)}
                  onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                  onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                  onDeleteConfirm={() => setConfirmDelete(s.id)}
                  onDeleteCancel={() => setConfirmDelete(null)}
                  onDelete={() => handleDelete(s.id)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Biker columns */}
        {bikers.map((biker) => {
          const bikerRoutes = bikerSessions.get(biker.username) ?? [];
          return (
            <div className="dashboard-column" key={biker.id}>
              <div className="dashboard-column-header">
                <div className="dashboard-column-biker">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="18.5" cy="17.5" r="3.5" />
                    <circle cx="5.5" cy="17.5" r="3.5" />
                    <path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2" />
                  </svg>
                  <span className="dashboard-column-title">{biker.username}</span>
                </div>
                <span className="dashboard-column-count">{bikerRoutes.length}</span>
              </div>
              <div className="dashboard-column-cards">
                {bikerRoutes.map((s) => (
                  <SessionCard
                    key={s.id}
                    session={s}
                    bikers={bikers}
                    assignDropdown={assignDropdown}
                    confirmDelete={confirmDelete}
                    onView={() => onViewSession(s.id)}
                    onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                    onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                    onDeleteConfirm={() => setConfirmDelete(s.id)}
                    onDeleteCancel={() => setConfirmDelete(null)}
                    onDelete={() => handleDelete(s.id)}
                  />
                ))}
                {bikerRoutes.length === 0 && (
                  <div className="dashboard-empty">No routes assigned</div>
                )}
              </div>
              <button
                className="btn btn-ghost dashboard-upload-btn"
                onClick={() => handleUploadClick(biker.id)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Upload for {biker.username}
              </button>
            </div>
          );
        })}

        {bikers.length === 0 && unassigned.length === 0 && (
          <div className="dashboard-no-data">
            <p>No bikers or routes yet.</p>
            <p>Bikers will appear here after they sign in.</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface SessionCardProps {
  session: SessionSummary;
  bikers: User[];
  assignDropdown: string | null;
  confirmDelete: string | null;
  onView: () => void;
  onAssignOpen: () => void;
  onAssign: (ownerId: number) => void;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
  onDelete: () => void;
}

function SessionCard({
  session,
  bikers,
  assignDropdown,
  confirmDelete,
  onView,
  onAssignOpen,
  onAssign,
  onDeleteConfirm,
  onDeleteCancel,
  onDelete,
}: SessionCardProps) {
  const isAssigning = assignDropdown === session.id;
  const isConfirmingDelete = confirmDelete === session.id;

  return (
    <div className="session-card">
      <div className="session-card-info" onClick={onView} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onView(); }}>
        <span className="session-card-date">{formatDate(session.created_at)}</span>
        <span className="session-card-stops">
          {session.stop_count} stop{session.stop_count !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="session-card-actions">
        {/* View */}
        <button className="session-card-btn" onClick={onView} title="View route on map">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        </button>
        {/* Assign */}
        <div className="session-card-assign-wrap">
          <button className="session-card-btn" onClick={onAssignOpen} title="Assign to biker">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <line x1="19" y1="8" x2="19" y2="14" />
              <line x1="22" y1="11" x2="16" y2="11" />
            </svg>
          </button>
          {isAssigning && (
            <>
              <div className="session-card-assign-overlay" onClick={onAssignOpen} />
              <div className="session-card-assign-dropdown">
                {bikers.map((b) => (
                  <button
                    key={b.id}
                    className={`session-card-assign-option ${b.username === session.owner_name ? "session-card-assign-option--current" : ""}`}
                    onClick={() => onAssign(b.id)}
                  >
                    {b.username}
                    {b.username === session.owner_name && " (current)"}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
        {/* Delete */}
        <button className="session-card-btn session-card-btn--danger" onClick={onDeleteConfirm} title="Delete route">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>

      {/* Delete confirmation */}
      {isConfirmingDelete && (
        <div className="session-card-confirm">
          <span>Delete this route?</span>
          <div className="session-card-confirm-actions">
            <button className="btn btn-sm btn-ghost" onClick={onDeleteCancel}>Cancel</button>
            <button className="btn btn-sm session-card-confirm-delete" onClick={onDelete}>Delete</button>
          </div>
        </div>
      )}
    </div>
  );
}
