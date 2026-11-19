import type { SessionResponse } from "../types";
import { stopZip } from "../utils/zipConflicts";

interface MoveZipModalProps {
  zip: string;
  routes: { session: SessionResponse; color: string }[];
  busy: boolean;
  onMove: (toSessionId: string) => void;
  onClose: () => void;
}

/** Pick the biker who should carry every stop of one postal code. */
export function MoveZipModal({ zip, routes, busy, onMove, onClose }: MoveZipModalProps) {
  const owner = (s: SessionResponse) => s.owner_name ?? "Unassigned";
  const inZip = (s: SessionResponse) => s.stops.filter((st) => !st.excluded && stopZip(st) === zip).length;
  const total = routes.reduce((n, r) => n + inZip(r.session), 0);
  return (
    <div className="move-stop-overlay" onClick={onClose}>
      <div
        className="move-stop-card"
        role="dialog"
        aria-label="Move postal code to another biker"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Move postal code {zip}</h2>
        <div className="move-stop-stop">
          <span>
            All <b>{total}</b> stops of {zip} go to the biker you pick.
          </span>
        </div>
        <ul className="move-stop-list">
          {routes.map((r) => {
            const s = r.session;
            const mine = inZip(s);
            const locked = s.status === "in_progress" || s.status === "finished";
            const after = s.stops.length - mine + total;
            return (
              <li key={s.id}>
                <button
                  className="move-stop-option"
                  disabled={locked || busy || mine === total}
                  onClick={() => onMove(s.id)}
                >
                  <span className="move-stop-option-name">
                    <span className="cluster-stop-dot" style={{ background: r.color }} />
                    <b>{owner(s)}</b> · {s.name}
                  </span>
                  <span className="move-stop-meta">
                    {locked
                      ? "already riding"
                      : mine === total
                        ? "already has all"
                        : `${s.stops.length} → ${after} stops`}
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
