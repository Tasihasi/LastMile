import type { DeliveryStop, SessionResponse } from "../types";

interface MoveStopModalProps {
  stop: DeliveryStop;
  from: SessionResponse;
  routes: { session: SessionResponse; color: string }[];
  busy: boolean;
  onMove: (toSessionId: string) => void;
  onClose: () => void;
}

/** Overlay on top of the split-review map: pick the biker who should carry a stop. */
export function MoveStopModal({ stop, from, routes, busy, onMove, onClose }: MoveStopModalProps) {
  const owner = (s: SessionResponse) => s.owner_name ?? "Unassigned";
  return (
    <div className="move-stop-overlay" onClick={onClose}>
      <div
        className="move-stop-card"
        role="dialog"
        aria-label="Move stop to another biker"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Move stop to another biker</h2>
        <div className="move-stop-stop">
          <strong>{stop.name}</strong>
          {stop.raw_address && <span>{stop.raw_address}</span>}
          <span className="move-stop-current">
            Currently carried by <b>{owner(from)}</b> ({from.name})
          </span>
        </div>
        <ul className="move-stop-list">
          {routes
            .filter((r) => r.session.id !== from.id)
            .map((r) => {
              const locked =
                r.session.status === "in_progress" || r.session.status === "finished";
              return (
                <li key={r.session.id}>
                  <button
                    className="move-stop-option"
                    disabled={locked || busy}
                    onClick={() => onMove(r.session.id)}
                  >
                    <span className="move-stop-option-name">
                      <span className="cluster-stop-dot" style={{ background: r.color }} />
                      <b>{owner(r.session)}</b> · {r.session.name}
                    </span>
                    <span className="move-stop-meta">
                      {locked ? "already riding" : `${r.session.stops.length} stops`}
                    </span>
                  </button>
                </li>
              );
            })}
        </ul>
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  );
}
