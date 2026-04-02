import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionSummary, User } from "../types";
import { formatDuration, formatDistance } from "../utils/format";
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

// Drop zone identifier: biker id or "unassigned"
type DropTarget = number | "unassigned";

export function PlannerDashboard({ onViewSession }: PlannerDashboardProps) {
  const [bikers, setBikers] = useState<User[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignDropdown, setAssignDropdown] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | undefined>();
  const [dragOverTarget, setDragOverTarget] = useState<DropTarget | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

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

  // Drag & drop handlers
  const handleDragStart = (sessionId: string) => {
    setDraggingId(sessionId);
  };

  const handleDragEnd = () => {
    setDraggingId(null);
    setDragOverTarget(null);
  };

  const handleDragOver = (e: React.DragEvent, target: DropTarget) => {
    e.preventDefault();
    setDragOverTarget(target);
  };

  const handleDragLeave = () => {
    setDragOverTarget(null);
  };

  const handleDrop = async (e: React.DragEvent, target: DropTarget) => {
    e.preventDefault();
    setDragOverTarget(null);
    setDraggingId(null);

    if (!draggingId) return;

    if (target === "unassigned") {
      // Can't unassign via drag for now — would need a backend endpoint
      return;
    }

    await handleAssign(draggingId, target);
  };

  // Separate finished routes
  const finishedSessions = sessions.filter((s) => s.status === "finished");
  const activeSessions = sessions.filter((s) => s.status !== "finished");

  // Group active sessions by owner
  const unassigned = activeSessions.filter((s) => !s.owner_name);
  const bikerSessions = new Map<string, SessionSummary[]>();
  for (const biker of bikers) {
    bikerSessions.set(
      biker.username,
      activeSessions.filter((s) => s.owner_name === biker.username)
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

      <div className="dashboard-layout">
        {/* Left: Unassigned routes */}
        {unassigned.length > 0 && (
          <div
            className={`dashboard-unassigned ${dragOverTarget === "unassigned" ? "dashboard-drop-active" : ""}`}
            onDragOver={(e) => handleDragOver(e, "unassigned")}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, "unassigned")}
          >
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
                    isDragging={draggingId === s.id}
                    onDragStart={() => handleDragStart(s.id)}
                    onDragEnd={handleDragEnd}
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
          </div>
        )}

        {/* Right: Bikers stacked vertically */}
        <div className="dashboard-bikers">
          {bikers.map((biker) => {
            const bikerRoutes = bikerSessions.get(biker.username) ?? [];
            const isDropTarget = dragOverTarget === biker.id;
            return (
              <div
                className={`dashboard-column ${isDropTarget ? "dashboard-drop-active" : ""}`}
                key={biker.id}
                onDragOver={(e) => handleDragOver(e, biker.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, biker.id)}
              >
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
                      isDragging={draggingId === s.id}
                      onDragStart={() => handleDragStart(s.id)}
                      onDragEnd={handleDragEnd}
                      onView={() => onViewSession(s.id)}
                      onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                      onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                      onDeleteConfirm={() => setConfirmDelete(s.id)}
                      onDeleteCancel={() => setConfirmDelete(null)}
                      onDelete={() => handleDelete(s.id)}
                    />
                  ))}
                  {bikerRoutes.length === 0 && (
                    <div className="dashboard-empty">
                      {draggingId ? "Drop here to assign" : "No routes assigned"}
                    </div>
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

      {/* Finished Routes Bin */}
      {finishedSessions.length > 0 && (
        <div className="dashboard-finished">
          <div className="dashboard-finished-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span className="dashboard-column-title">Finished Routes</span>
            <span className="dashboard-column-count">{finishedSessions.length}</span>
          </div>
          <div className="dashboard-finished-cards">
            {finishedSessions.map((s) => (
              <SessionCard
                key={s.id}
                session={s}
                bikers={bikers}
                assignDropdown={assignDropdown}
                confirmDelete={confirmDelete}
                isDragging={draggingId === s.id}
                onDragStart={() => handleDragStart(s.id)}
                onDragEnd={handleDragEnd}
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
    </div>
  );
}

interface SessionCardProps {
  session: SessionSummary;
  bikers: User[];
  assignDropdown: string | null;
  confirmDelete: string | null;
  isDragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
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
  isDragging,
  onDragStart,
  onDragEnd,
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
    <div
      className={`session-card ${isDragging ? "session-card--dragging" : ""}`}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
    >
      <div className="session-card-drag-handle">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <circle cx="9" cy="6" r="1.5" />
          <circle cx="15" cy="6" r="1.5" />
          <circle cx="9" cy="12" r="1.5" />
          <circle cx="15" cy="12" r="1.5" />
          <circle cx="9" cy="18" r="1.5" />
          <circle cx="15" cy="18" r="1.5" />
        </svg>
      </div>
      <div className="session-card-info" onClick={onView} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onView(); }}>
        <div className="session-card-name-row">
          <span className="session-card-name">{session.name || "Untitled Route"}</span>
          {session.status === "in_progress" && (
            <span className="session-card-status session-card-status--active">In Progress</span>
          )}
          {session.status === "finished" && (
            <span className="session-card-status session-card-status--finished">Done</span>
          )}
        </div>
        <div className="session-card-meta">
          <span className="session-card-stops">
            {session.status === "in_progress" || session.status === "finished"
              ? `${session.delivered_count + session.not_received_count}/${session.stop_count} stops`
              : `${session.stop_count} stop${session.stop_count !== 1 ? "s" : ""}`
            }
          </span>
          {session.total_duration != null && (
            <span className="session-card-duration">
              {formatDuration(session.total_duration)} / {formatDistance(session.total_distance ?? 0)}
            </span>
          )}
        </div>
        {session.status === "in_progress" && session.current_stop_name && (
          <div className="session-card-progress">
            <span className="session-card-progress-dot" />
            <span className="session-card-progress-text">Heading to: {session.current_stop_name}</span>
          </div>
        )}
        {session.status === "finished" && session.not_received_count > 0 && (
          <div className="session-card-progress session-card-progress--warning">
            <span className="session-card-progress-text">{session.not_received_count} not received</span>
          </div>
        )}
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
