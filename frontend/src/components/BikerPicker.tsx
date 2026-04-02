import { useEffect, useState } from "react";
import type { User } from "../types";
import { listBikers } from "../api/client";

interface BikerPickerProps {
  selectedBikerId: number | null;
  onSelectBiker: (biker: User | null) => void;
}

export function BikerPicker({ selectedBikerId, onSelectBiker }: BikerPickerProps) {
  const [bikers, setBikers] = useState<User[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    listBikers().then(setBikers).catch(() => {});
  }, []);

  const selected = bikers.find((b) => b.id === selectedBikerId) ?? null;

  return (
    <div className="biker-picker">
      <button
        className="biker-picker-trigger"
        onClick={() => setOpen(!open)}
        title="Select biker"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
        </svg>
        <span>{selected ? selected.username : "All bikers"}</span>
        <svg className="biker-picker-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <>
          <div className="biker-picker-overlay" onClick={() => setOpen(false)} />
          <div className="biker-picker-dropdown">
            <button
              className={`biker-picker-option ${selectedBikerId === null ? "biker-picker-option--active" : ""}`}
              onClick={() => { onSelectBiker(null); setOpen(false); }}
            >
              All bikers
            </button>
            {bikers.map((biker) => (
              <button
                key={biker.id}
                className={`biker-picker-option ${biker.id === selectedBikerId ? "biker-picker-option--active" : ""}`}
                onClick={() => { onSelectBiker(biker); setOpen(false); }}
              >
                {biker.username}
              </button>
            ))}
            {bikers.length === 0 && (
              <div className="biker-picker-empty">No bikers yet</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
