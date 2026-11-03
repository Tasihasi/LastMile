import { HoldToConfirmButton } from "./HoldToConfirmButton";
import { useState } from "react";
import type { DeliveryStop } from "../types";
import { getSession, moveStop, removeStop } from "../api/client";
import { useSplitSubRoutes } from "../hooks/useSplitSubRoutes";
import { useToast } from "../hooks/useToast";

interface StopKanbanBoardProps {
  parentSessionId: string;
  onBack: () => void;
}

interface DragData {
  stopId: number;
  fromRouteId: string;
}

const DRAG_MIME = "application/x-lastmile-stop";

/**
 * Drag-and-drop board for a split route: one column per sub-route, stops as
 * cards that can be dragged onto a sibling column to reassign them to a
 * different biker.
 */
export function StopKanbanBoard({ parentSessionId, onBack }: StopKanbanBoardProps) {
  const { subRoutes, setSubRoutes, parentSession, loading, error, setError } =
    useSplitSubRoutes(parentSessionId);
  const { showToast } = useToast();
  const [draggingStopId, setDraggingStopId] = useState<number | null>(null);
  const [dragOverRouteId, setDragOverRouteId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleDrop = async (toRouteId: string, data: DragData) => {
    setDragOverRouteId(null);
    setDraggingStopId(null);
    if (data.fromRouteId === toRouteId) return;

    setBusy(true);
    try {
      await moveStop(data.fromRouteId, data.stopId, toRouteId);
      const [fromUpdated, toUpdated] = await Promise.all([
        getSession(data.fromRouteId),
        getSession(toRouteId),
      ]);
      setSubRoutes((prev) =>
        prev.map((s) => {
          if (s.id === data.fromRouteId) return fromUpdated;
          if (s.id === toRouteId) return toUpdated;
          return s;
        })
      );
    } catch {
      setError("Failed to move stop.");
      showToast("Failed to move stop", "error");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (routeId: string, stopId: number) => {
    try {
      await removeStop(routeId, stopId);
      const updated = await getSession(routeId);
      setSubRoutes((prev) => prev.map((s) => (s.id === routeId ? updated : s)));
      showToast("Stop removed");
    } catch {
      showToast("Failed to remove stop", "error");
    }
  };

  if (loading) {
    return (
      <div className="cluster-review-loading">
        <span className="upload-spinner" />
      </div>
    );
  }

  if (error && subRoutes.length === 0) {
    return (
      <div className="cluster-review-empty">
        <p>{error}</p>
        <button className="btn btn-ghost" onClick={onBack}>
          Back
        </button>
      </div>
    );
  }

  return (
    <div className="stop-kanban">
      <div className="cluster-review-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Split Review
        </button>
        <h3>{parentSession?.name || "Stop Board"}</h3>
        <span className="stop-kanban-hint">Drag a stop onto another column to reassign it</span>
      </div>

      {error && (
        <div className="cluster-review-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="stop-kanban-board">
        {subRoutes.map((route) => {
          const locked = route.status === "in_progress";
          const isOver = dragOverRouteId === route.id;
          return (
            <div
              key={route.id}
              className={`stop-kanban-column ${isOver ? "stop-kanban-column--over" : ""} ${locked ? "stop-kanban-column--locked" : ""}`}
              onDragOver={(e) => {
                if (locked) return;
                e.preventDefault();
                if (dragOverRouteId !== route.id) setDragOverRouteId(route.id);
              }}
              onDragLeave={(e) => {
                if (e.currentTarget.contains(e.relatedTarget as Node)) return;
                setDragOverRouteId((cur) => (cur === route.id ? null : cur));
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (locked) return;
                const raw = e.dataTransfer.getData(DRAG_MIME) || e.dataTransfer.getData("text/plain");
                if (!raw) return;
                try {
                  const data = JSON.parse(raw) as DragData;
                  handleDrop(route.id, data);
                } catch {
                  // ignore malformed drag payload
                }
              }}
            >
              <div className="stop-kanban-column-header">
                <span className="stop-kanban-column-title">
                  {route.owner_name || "Unassigned"}
                </span>
                <span className="stop-kanban-column-meta">
                  {route.name} &middot; {route.stops.length} stops
                </span>
                {locked && (
                  <span className="stop-kanban-column-locked-badge" title="Route in progress — stops locked">
                    In progress
                  </span>
                )}
              </div>

              <div className="stop-kanban-column-body">
                {route.stops.length === 0 && (
                  <div className="stop-kanban-empty">No stops — drop one here</div>
                )}
                {route.stops.map((stop) => (
                  <StopCard
                    key={stop.id}
                    stop={stop}
                    routeId={route.id}
                    locked={locked}
                    dragging={draggingStopId === stop.id}
                    disabled={busy}
                    onDragStart={() => setDraggingStopId(stop.id)}
                    onDragEnd={() => {
                      setDraggingStopId(null);
                      setDragOverRouteId(null);
                    }}
                    onRemove={() => handleRemove(route.id, stop.id)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StopCard({
  stop,
  routeId,
  locked,
  dragging,
  disabled,
  onDragStart,
  onDragEnd,
  onRemove,
}: {
  stop: DeliveryStop;
  routeId: string;
  locked: boolean;
  dragging: boolean;
  disabled: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={`stop-kanban-card ${dragging ? "stop-kanban-card--dragging" : ""}`}
      draggable={!locked && !disabled}
      onDragStart={(e) => {
        const data: DragData = { stopId: stop.id, fromRouteId: routeId };
        e.dataTransfer.setData(DRAG_MIME, JSON.stringify(data));
        e.dataTransfer.setData("text/plain", JSON.stringify(data));
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
    >
      <div className="stop-kanban-card-main">
        <span className="stop-kanban-card-name">{stop.name}</span>
        {stop.raw_address && (
          <span className="stop-kanban-card-address">{stop.raw_address}</span>
        )}
      </div>
      {!locked && (
        <HoldToConfirmButton
          className="stop-kanban-card-remove"
          title="Hold to remove stop from the plan"
          aria-label="Hold to remove stop from the plan"
          onConfirm={onRemove}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </HoldToConfirmButton>
      )}
    </div>
  );
}
