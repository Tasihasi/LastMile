import { useEffect, useMemo, useState } from "react";
import type {
  DistrictsResponse,
  SessionSummary,
  SplitAssignment,
  User,
} from "../types";
import { clusterSession, getSessionDistricts } from "../api/client";
import { useToast } from "../hooks/useToast";

interface BikerRow {
  selected: boolean;
  targetStops: number;
  districtOnly: boolean;
  district: number | null;
}

interface SplitPlannerModalProps {
  session: SessionSummary;
  bikers: User[];
  onClose: () => void;
  /** Called with the parent session id after a successful split. */
  onSplit: (parentId: string) => void;
}

/** Distribute total stops evenly across n bikers (first rows get the remainder). */
function evenSplit(total: number, n: number): number[] {
  if (n <= 0) return [];
  const base = Math.floor(total / n);
  const extra = total % n;
  return Array.from({ length: n }, (_, i) => base + (i < extra ? 1 : 0));
}

export function SplitPlannerModal({
  session,
  bikers,
  onClose,
  onSplit,
}: SplitPlannerModalProps) {
  const [rows, setRows] = useState<Map<number, BikerRow>>(() => {
    const targets = evenSplit(session.stop_count, bikers.length);
    return new Map(
      bikers.map((b, i) => [
        b.id,
        { selected: true, targetStops: targets[i] ?? 0, districtOnly: false, district: null },
      ])
    );
  });
  const [districts, setDistricts] = useState<DistrictsResponse | null>(null);
  const [splitting, setSplitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { showToast } = useToast();

  useEffect(() => {
    let cancelled = false;
    getSessionDistricts(session.id)
      .then((d) => {
        if (!cancelled) setDistricts(d);
      })
      .catch(() => {
        // Districts are optional — the toggle is just hidden without them.
      });
    return () => {
      cancelled = true;
    };
  }, [session.id]);

  const updateRow = (bikerId: number, patch: Partial<BikerRow>) => {
    setRows((prev) => {
      const next = new Map(prev);
      const row = next.get(bikerId);
      if (row) next.set(bikerId, { ...row, ...patch });
      return next;
    });
  };

  const toggleBiker = (bikerId: number) => {
    setRows((prev) => {
      const next = new Map(prev);
      const row = next.get(bikerId);
      if (!row) return prev;
      next.set(bikerId, { ...row, selected: !row.selected });
      // Rebalance targets evenly across the new selection
      const selectedIds = bikers.filter((b) => next.get(b.id)?.selected).map((b) => b.id);
      const targets = evenSplit(session.stop_count, selectedIds.length);
      selectedIds.forEach((id, i) => {
        const r = next.get(id)!;
        next.set(id, { ...r, targetStops: targets[i] });
      });
      return next;
    });
  };

  const selectedBikers = bikers.filter((b) => rows.get(b.id)?.selected);
  const targetSum = selectedBikers.reduce(
    (sum, b) => sum + (rows.get(b.id)?.targetStops ?? 0),
    0
  );
  const oversized = selectedBikers.some(
    (b) => (rows.get(b.id)?.targetStops ?? 0) > 48
  );

  const districtOptions = useMemo(() => districts?.districts ?? [], [districts]);

  const handleSplit = async () => {
    setError(null);
    setSplitting(true);
    try {
      if (selectedBikers.length === 0) {
        // No bikers picked — fall back to automatic geographic splitting.
        await clusterSession(session.id);
        showToast(`Split "${session.name}" automatically`);
      } else {
        const assignments: SplitAssignment[] = selectedBikers.map((b) => {
          const row = rows.get(b.id)!;
          return {
            biker_id: b.id,
            target_stops: row.targetStops,
            district: row.districtOnly ? row.district : null,
          };
        });
        await clusterSession(session.id, { assignments });
        showToast(`Split "${session.name}" between ${selectedBikers.length} biker${selectedBikers.length !== 1 ? "s" : ""}`);
      }
      onSplit(session.id);
    } catch (err) {
      const data = (err as { response?: { data?: { error?: string } } })?.response?.data;
      setError(data?.error || "Failed to split the route.");
      setSplitting(false);
    }
  };

  const canSplit =
    !splitting &&
    selectedBikers.every((b) => {
      const row = rows.get(b.id)!;
      return !row.districtOnly || row.district != null;
    });

  return (
    <div className="split-planner-overlay" onClick={onClose}>
      <div
        className="split-planner"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Split route planner"
      >
        <div className="split-planner-header">
          <div>
            <h3>Split “{session.name || "Route"}”</h3>
            <span className="split-planner-subtitle">
              {session.stop_count} stops — choose bikers, workloads and districts
            </span>
          </div>
          <button className="split-planner-close" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="split-planner-error">
            <span>{error}</span>
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        <div className="split-planner-rows">
          {bikers.length === 0 && (
            <p className="split-planner-empty">
              No bikers yet — bikers appear here after they sign in. You can
              still split the route and assign later.
            </p>
          )}
          {bikers.map((biker) => {
            const row = rows.get(biker.id)!;
            return (
              <div
                key={biker.id}
                className={`split-planner-row ${row.selected ? "" : "split-planner-row--disabled"}`}
              >
                <label className="split-planner-biker">
                  <input
                    type="checkbox"
                    checked={row.selected}
                    onChange={() => toggleBiker(biker.id)}
                  />
                  <span className="split-planner-biker-name">{biker.username}</span>
                </label>

                {row.selected && (
                  <div className="split-planner-row-controls">
                    <label className="split-planner-target">
                      <span>≈ stops</span>
                      <input
                        type="number"
                        min={0}
                        max={session.stop_count}
                        value={row.targetStops}
                        onChange={(e) =>
                          updateRow(biker.id, {
                            targetStops: Math.max(0, parseInt(e.target.value) || 0),
                          })
                        }
                        title="Approximate number of stops for this biker (e.g. fewer for a half-day shift)"
                      />
                    </label>

                    {districtOptions.length > 0 && (
                      <div className="split-planner-district">
                        <label className="split-planner-toggle" title="Only give this biker stops from a single city district">
                          <input
                            type="checkbox"
                            checked={row.districtOnly}
                            onChange={(e) =>
                              updateRow(biker.id, {
                                districtOnly: e.target.checked,
                                district: e.target.checked
                                  ? row.district ?? districtOptions[0].district
                                  : row.district,
                              })
                            }
                          />
                          <span className="split-planner-toggle-track">
                            <span className="split-planner-toggle-thumb" />
                          </span>
                          <span className="split-planner-toggle-label">Single district</span>
                        </label>
                        {row.districtOnly && (
                          <select
                            value={row.district ?? ""}
                            onChange={(e) =>
                              updateRow(biker.id, { district: parseInt(e.target.value) })
                            }
                          >
                            {districtOptions.map((d) => (
                              <option key={d.district} value={d.district}>
                                {d.label} ({d.stop_count} stops)
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="split-planner-footer">
          <div className="split-planner-summary">
            <span className={targetSum === session.stop_count ? "" : "split-planner-summary--off"}>
              {targetSum}/{session.stop_count} stops planned
            </span>
            {targetSum !== session.stop_count && selectedBikers.length > 0 && (
              <span className="split-planner-hint">
                Counts are approximate — every stop is always placed.
              </span>
            )}
            {oversized && (
              <span className="split-planner-warning">
                A route over 48 stops cannot be optimized in one go.
              </span>
            )}
            {districts != null && districts.unknown_district_stops > 0 && (
              <span className="split-planner-hint">
                {districts.unknown_district_stops} stop
                {districts.unknown_district_stops !== 1 ? "s" : ""} without a
                recognized district.
              </span>
            )}
          </div>
          <div className="split-planner-actions">
            <button className="btn btn-ghost" onClick={onClose} disabled={splitting}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSplit} disabled={!canSplit}>
              {splitting ? (
                <>
                  <span className="upload-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  Splitting...
                </>
              ) : selectedBikers.length === 0 ? (
                "Split automatically"
              ) : (
                `Split between ${selectedBikers.length} biker${selectedBikers.length !== 1 ? "s" : ""}`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
