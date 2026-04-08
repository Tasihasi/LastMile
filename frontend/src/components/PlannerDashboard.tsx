import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionSummary, User } from "../types";
import { formatDuration, formatDistance, formatTime } from "../utils/format";
import { useSettings } from "../hooks/useSettings";
import {
  listBikers,
  listSessions,
  deleteSession,
  assignSession,
  renameSession,
  uploadFile as apiUpload,
  clusterSession,
} from "../api/client";
import { FinishedRouteDetail } from "./FinishedRouteDetail";

interface PlannerDashboardProps {
  onViewSession: (sessionId: string) => void;
  onOpenLiveMap?: () => void;
  onOpenMapView?: () => void;
  onClusterReview?: (parentSessionId: string) => void;
}

// Drop zone identifier: biker id or "unassigned"
type DropTarget = number | "unassigned";

export function PlannerDashboard({ onViewSession, onOpenLiveMap, onOpenMapView, onClusterReview }: PlannerDashboardProps) {
  const [bikers, setBikers] = useState<User[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignDropdown, setAssignDropdown] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | undefined>();
  const [dragOverTarget, setDragOverTarget] = useState<DropTarget | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [finishedDetailId, setFinishedDetailId] = useState<string | null>(null);
  const [clusteringId, setClusteringId] = useState<string | null>(null);

  const { settings } = useSettings();
  const [bikerFilter, setBikerFilter] = useState<"active" | "inactive" | "all">("active");

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

  const handleAssign = async (sessionId: string, ownerId: number | null) => {
    try {
      await assignSession(sessionId, ownerId);
      refresh();
    } catch { /* ignore */ }
    setAssignDropdown(null);
  };

  const handleRename = async (sessionId: string, name: string) => {
    try {
      await renameSession(sessionId, name);
      setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, name } : s)));
    } catch { /* ignore */ }
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

  const handleCluster = async (sessionId: string) => {
    setClusteringId(sessionId);
    try {
      const result = await clusterSession(sessionId);
      if (onClusterReview) {
        onClusterReview(result.parent_id);
      } else {
        refresh();
      }
    } catch {
      // ignore
    } finally {
      setClusteringId(null);
    }
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
      await handleAssign(draggingId, null);
      return;
    }

    await handleAssign(draggingId, target);
  };

  // Separate finished, split, and child routes
  const finishedSessions = sessions.filter((s) => s.status === "finished");
  const splitSessions = sessions.filter((s) => s.status === "split");
  const childSessionIds = new Set(sessions.filter((s) => s.parent_id != null).map((s) => s.id));
  const activeSessions = sessions.filter(
    (s) => s.status !== "finished" && s.status !== "split" && !childSessionIds.has(s.id)
  );
  const activeCount = sessions.filter((s) => s.status === "in_progress").length;

  // Group active sessions by owner, in_progress always first
  const statusPriority = (s: SessionSummary) => s.status === "in_progress" ? 0 : 1;
  const unassigned = activeSessions.filter((s) => !s.owner_name);
  const bikerSessions = new Map<string, SessionSummary[]>();
  for (const biker of bikers) {
    bikerSessions.set(
      biker.username,
      activeSessions
        .filter((s) => s.owner_name === biker.username)
        .sort((a, b) => statusPriority(a) - statusPriority(b))
    );
  }

  // Filter bikers based on activity filter
  const activeBikerNames = new Set(
    sessions.filter((s) => s.status === "in_progress").map((s) => s.owner_name)
  );
  const filteredBikers = bikers.filter((b) => {
    if (bikerFilter === "active") return activeBikerNames.has(b.username);
    if (bikerFilter === "inactive") return !activeBikerNames.has(b.username);
    return true; // "all"
  });

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
        <div className="dashboard-header-actions">
          <div className="dashboard-filter">
            {(["active", "inactive", "all"] as const).map((f) => (
              <button
                key={f}
                className={`dashboard-filter-btn ${bikerFilter === f ? "dashboard-filter-btn--active" : ""}`}
                onClick={() => setBikerFilter(f)}
              >
                {f === "active" ? "Active" : f === "inactive" ? "Inactive" : "All"} Bikers
              </button>
            ))}
          </div>
          {onOpenMapView && (
            <button className="btn btn-ghost btn-sm" onClick={onOpenMapView}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              My Map
            </button>
          )}
          {onOpenLiveMap && activeCount > 0 && (
            <button className="btn btn-live-map btn-sm" onClick={onOpenLiveMap}>
              <span className="btn-live-dot" />
              Live Map ({activeCount})
            </button>
          )}
          <button className="btn btn-primary btn-sm" onClick={() => handleUploadClick()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Upload Route
          </button>
        </div>
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
                  <div key={s.id} className="session-card-wrapper">
                    {s.stop_count > 48 && s.status === "not_started" && (
                      <ClusterBanner
                        session={s}
                        clusteringId={clusteringId}
                        onCluster={() => handleCluster(s.id)}
                      />
                    )}
                    <SessionCard
                      session={s}
                      bikers={bikers}
                      assignDropdown={assignDropdown}
                      confirmDelete={confirmDelete}
                      isDragging={draggingId === s.id}
                      dwellMinutes={settings.dwellMinutes}
                      onDragStart={() => handleDragStart(s.id)}
                      onDragEnd={handleDragEnd}
                      onView={() => onViewSession(s.id)}
                      onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                      onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                      onDeleteConfirm={() => setConfirmDelete(s.id)}
                      onDeleteCancel={() => setConfirmDelete(null)}
                      onDelete={() => handleDelete(s.id)}
                      onRename={(name) => handleRename(s.id, name)}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Split sessions */}
        {splitSessions.length > 0 && (
          <div className="dashboard-split">
            <div className="dashboard-column">
              <div className="dashboard-column-header">
                <div className="dashboard-column-biker">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="3" />
                    <circle cx="5" cy="6" r="2" />
                    <circle cx="19" cy="6" r="2" />
                    <circle cx="5" cy="18" r="2" />
                    <circle cx="19" cy="18" r="2" />
                  </svg>
                  <span className="dashboard-column-title">Split Routes</span>
                </div>
                <span className="dashboard-column-count">{splitSessions.length}</span>
              </div>
              <div className="dashboard-column-cards">
                {splitSessions.map((s) => (
                  <div
                    key={s.id}
                    className="session-card session-card--split"
                    onClick={() => onClusterReview?.(s.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") onClusterReview?.(s.id); }}
                  >
                    <div className="session-card-info">
                      <div className="session-card-name-row">
                        <span className="session-card-name">{s.name || "Untitled Route"}</span>
                        <span className="session-card-status session-card-status--split">
                          {s.sub_route_count} routes
                        </span>
                      </div>
                      <div className="session-card-meta">
                        <span className="session-card-stops">{s.stop_count} stops total</span>
                      </div>
                    </div>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 20, height: 20, flexShrink: 0, opacity: 0.5 }}>
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Right: Bikers stacked vertically */}
        <div className="dashboard-bikers">
          {filteredBikers.map((biker) => {
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
                    <div key={s.id} className="session-card-wrapper">
                      {s.stop_count > 48 && s.status === "not_started" && (
                        <ClusterBanner
                          session={s}
                          clusteringId={clusteringId}
                          onCluster={() => handleCluster(s.id)}
                        />
                      )}
                      <SessionCard
                        session={s}
                        bikers={bikers}
                        assignDropdown={assignDropdown}
                        confirmDelete={confirmDelete}
                        isDragging={draggingId === s.id}
                        dwellMinutes={settings.dwellMinutes}
                        onDragStart={() => handleDragStart(s.id)}
                        onDragEnd={handleDragEnd}
                        onView={() => onViewSession(s.id)}
                        onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                        onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                        onDeleteConfirm={() => setConfirmDelete(s.id)}
                        onDeleteCancel={() => setConfirmDelete(null)}
                        onDelete={() => handleDelete(s.id)}
                        onRename={(name) => handleRename(s.id, name)}
                      />
                    </div>
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

          {filteredBikers.length === 0 && (
            <div className="dashboard-no-data">
              {bikers.length === 0 ? (
                <>
                  <p>No bikers or routes yet.</p>
                  <p>Bikers will appear here after they sign in.</p>
                </>
              ) : (
                <p>No {bikerFilter === "active" ? "active" : "inactive"} bikers right now.</p>
              )}
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
                dwellMinutes={settings.dwellMinutes}
                onDragStart={() => handleDragStart(s.id)}
                onDragEnd={handleDragEnd}
                onView={() => setFinishedDetailId(s.id)}
                onAssignOpen={() => setAssignDropdown(assignDropdown === s.id ? null : s.id)}
                onAssign={(ownerId) => handleAssign(s.id, ownerId)}
                onDeleteConfirm={() => setConfirmDelete(s.id)}
                onDeleteCancel={() => setConfirmDelete(null)}
                onDelete={() => handleDelete(s.id)}
                onRename={(name) => handleRename(s.id, name)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Finished Route Detail Panel */}
      {finishedDetailId && (
        <FinishedRouteDetail
          sessionId={finishedDetailId}
          onClose={() => setFinishedDetailId(null)}
          onViewMap={(id) => { setFinishedDetailId(null); onViewSession(id); }}
        />
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
  dwellMinutes: number;
  onDragStart: () => void;
  onDragEnd: () => void;
  onView: () => void;
  onAssignOpen: () => void;
  onAssign: (ownerId: number | null) => void;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
  onDelete: () => void;
  onRename: (name: string) => void;
}

function SessionCard({
  session,
  bikers,
  assignDropdown,
  confirmDelete,
  isDragging,
  dwellMinutes,
  onDragStart,
  onDragEnd,
  onView,
  onAssignOpen,
  onAssign,
  onDeleteConfirm,
  onDeleteCancel,
  onDelete,
  onRename,
}: SessionCardProps) {
  const isAssigning = assignDropdown === session.id;
  const isConfirmingDelete = confirmDelete === session.id;
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(session.name);
  const inputRef = useRef<HTMLInputElement>(null);

  const startEditing = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditName(session.name);
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commitRename = () => {
    const trimmed = editName.trim();
    if (trimmed && trimmed !== session.name) {
      onRename(trimmed);
    }
    setIsEditing(false);
  };

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
          {isEditing ? (
            <input
              ref={inputRef}
              className="session-card-name-input"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") setIsEditing(false);
              }}
              onClick={(e) => e.stopPropagation()}
              autoFocus
            />
          ) : (
            <span
              className="session-card-name"
              onDoubleClick={startEditing}
              title="Double-click to rename"
            >
              {session.name || "Untitled Route"}
            </span>
          )}
          {session.status === "in_progress" && (
            <span className="session-card-status session-card-status--active">In Progress</span>
          )}
          {session.status === "finished" && (
            <span className="session-card-status session-card-status--finished">Done</span>
          )}
          {session.status === "split" && (
            <span className="session-card-status session-card-status--split">Split</span>
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
        {session.status === "in_progress" && session.started_at && session.total_duration != null && (() => {
          const startMs = new Date(session.started_at).getTime();
          const totalSec = session.total_duration + session.stop_count * dwellMinutes * 60;
          const eta = new Date(startMs + totalSec * 1000);
          return (
            <div className="session-card-eta">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span>Back by ~{formatTime(eta)}</span>
            </div>
          );
        })()}
        {session.status === "finished" && session.not_received_count > 0 && (
          <div className="session-card-progress session-card-progress--warning">
            <span className="session-card-progress-text">{session.not_received_count} not received</span>
          </div>
        )}
      </div>
      <div className="session-card-actions">
        {/* Rename */}
        <button className="session-card-btn" onClick={startEditing} title="Rename route">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </button>
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
                {session.owner_name && (
                  <button
                    className="session-card-assign-option session-card-assign-option--unassign"
                    onClick={() => onAssign(null)}
                  >
                    Unassign
                  </button>
                )}
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

function ClusterBanner({ session, clusteringId, onCluster }: {
  session: SessionSummary;
  clusteringId: string | null;
  onCluster: () => void;
}) {
  return (
    <button
      className="cluster-banner"
      onClick={onCluster}
      disabled={clusteringId === session.id}
    >
      {clusteringId === session.id ? (
        <>
          <span className="upload-spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
          Splitting...
        </>
      ) : (
        <>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <circle cx="5" cy="6" r="2" />
            <circle cx="19" cy="6" r="2" />
            <circle cx="5" cy="18" r="2" />
            <circle cx="19" cy="18" r="2" />
          </svg>
          Split into {Math.ceil(session.stop_count / 48)} Routes
        </>
      )}
    </button>
  );
}
