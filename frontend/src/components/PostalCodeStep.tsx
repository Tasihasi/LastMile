import { useEffect, useMemo, useRef, useState } from "react";
import type { DeliveryStop } from "../types";
import { WizardFooter } from "./WizardFooter";

export interface StopPatch {
  excluded?: boolean;
  postal_code?: string;
}

interface PostalCodeStepProps {
  stops: DeliveryStop[];
  onUpdateStops: (ids: number[], patch: StopPatch) => Promise<void>;
  onBack: () => void;
  onNext: () => void;
}

const NEW_CODE = "__new__";

function MoveControl({
  stop,
  codes,
  onMove,
}: {
  stop: DeliveryStop;
  codes: string[];
  onMove: (code: string) => void;
}) {
  const [custom, setCustom] = useState<string | null>(null);

  if (custom !== null) {
    const valid = /^\d{4}$/.test(custom.trim());
    return (
      <form
        className="postal-move"
        onSubmit={(e) => {
          e.preventDefault();
          if (!valid) return;
          onMove(custom.trim());
          setCustom(null);
        }}
      >
        <input
          className="fix-row-input postal-move-input"
          value={custom}
          autoFocus
          inputMode="numeric"
          maxLength={4}
          placeholder="1234"
          aria-label={`New postal code for ${stop.name}`}
          onChange={(e) => setCustom(e.target.value)}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={!valid}>
          Move
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setCustom(null)}>
          Cancel
        </button>
      </form>
    );
  }

  return (
    <select
      className="postal-move-select"
      value=""
      aria-label={`Move ${stop.name} to another postal code`}
      onChange={(e) => {
        if (e.target.value === NEW_CODE) setCustom("");
        else if (e.target.value) onMove(e.target.value);
      }}
    >
      <option value="">Move to…</option>
      {codes
        .filter((c) => c !== stop.postal_code)
        .map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      <option value={NEW_CODE}>Other code…</option>
    </select>
  );
}

function GroupHeader({
  code,
  groupStops,
  open,
  onToggleOpen,
  onToggleIncluded,
}: {
  code: string;
  groupStops: DeliveryStop[];
  open: boolean;
  onToggleOpen: () => void;
  onToggleIncluded: (include: boolean) => void;
}) {
  const included = groupStops.filter((s) => !s.excluded).length;
  const checkbox = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (checkbox.current) {
      checkbox.current.indeterminate = included > 0 && included < groupStops.length;
    }
  }, [included, groupStops.length]);

  const label = code || "No postal code";
  return (
    <div className="postal-group-head">
      <input
        ref={checkbox}
        type="checkbox"
        checked={included > 0}
        aria-label={`Include postal code ${label}`}
        onChange={() => onToggleIncluded(included === 0)}
      />
      <span className="postal-code">{label}</span>
      <span className="postal-count">
        {included === groupStops.length
          ? `${groupStops.length} stops`
          : `${included} of ${groupStops.length} stops`}
      </span>
      <button
        type="button"
        className={`btn btn-ghost btn-sm postal-toggle ${open ? "postal-toggle--open" : ""}`}
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} addresses for ${label}`}
        onClick={onToggleOpen}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
    </div>
  );
}

export function PostalCodeStep({ stops, onUpdateStops, onBack, onNext }: PostalCodeStepProps) {
  const [openCodes, setOpenCodes] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  // Only stops with coordinates can be routed; the rest were left out in step 3.
  const routable = useMemo(() => stops.filter((s) => s.lat != null && s.lng != null), [stops]);
  const unroutable = stops.length - routable.length;
  const groups = useMemo(() => {
    const map = new Map<string, DeliveryStop[]>();
    for (const s of routable) {
      const list = map.get(s.postal_code) ?? [];
      list.push(s);
      map.set(s.postal_code, list);
    }
    // Unknown ("") last, otherwise ascending.
    return [...map.entries()].sort(([a], [b]) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b)));
  }, [routable]);
  const codes = groups.map(([c]) => c).filter(Boolean);
  const includedCount = routable.filter((s) => !s.excluded).length;

  const run = async (ids: number[], patch: StopPatch) => {
    setBusy(true);
    try {
      await onUpdateStops(ids, patch);
    } finally {
      setBusy(false);
    }
  };

  const toggleOpen = (code: string) =>
    setOpenCodes((prev) => {
      const next = new Set(prev);
      if (!next.delete(code)) next.add(code);
      return next;
    });

  return (
    <section className="wizard-card">
      <h2 className="wizard-title">Postal codes</h2>
      <p className="wizard-sub">
        Your files cover {groups.length} postal code{groups.length === 1 ? "" : "s"}. Untick the ones you do
        not want to plan today; open a code to see its addresses or move one to another code.
      </p>

      <div className="postal-toolbar">
        <strong>
          {includedCount} of {routable.length} stops included
        </strong>
        <span className="postal-toolbar-actions">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={busy}
            onClick={() => run(routable.filter((s) => s.excluded).map((s) => s.id), { excluded: false })}
          >
            Select all
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={busy}
            onClick={() => run(routable.filter((s) => !s.excluded).map((s) => s.id), { excluded: true })}
          >
            Select none
          </button>
        </span>
      </div>

      <ul className="postal-list">
        {groups.map(([code, groupStops]) => {
          const open = openCodes.has(code);
          return (
            <li key={code || "none"} className="postal-group">
              <GroupHeader
                code={code}
                groupStops={groupStops}
                open={open}
                onToggleOpen={() => toggleOpen(code)}
                onToggleIncluded={(include) => run(groupStops.map((s) => s.id), { excluded: !include })}
              />
              {open && (
                <ul className="postal-stops">
                  {groupStops.map((s) => (
                    <li key={s.id} className={`postal-stop ${s.excluded ? "postal-stop--off" : ""}`}>
                      <input
                        type="checkbox"
                        checked={!s.excluded}
                        disabled={busy}
                        aria-label={`Include ${s.name}`}
                        onChange={() => run([s.id], { excluded: !s.excluded })}
                      />
                      <span className="postal-stop-text">
                        <strong>{s.name}</strong>
                        <span>{s.raw_address || "—"}</span>
                      </span>
                      <MoveControl stop={s} codes={codes} onMove={(c) => run([s.id], { postal_code: c })} />
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      {unroutable > 0 && (
        <p className="wizard-result wizard-result--warn">
          {unroutable} stop{unroutable === 1 ? " has" : "s have"} no coordinates and will be left out.
        </p>
      )}

      <WizardFooter
        onBack={onBack}
        backLabel="Fix addresses"
        onNext={onNext}
        nextLabel="Continue"
        nextDisabled={includedCount < 2}
        busy={busy}
        hint={includedCount < 2 ? "Include at least 2 stops" : undefined}
      />
    </section>
  );
}
