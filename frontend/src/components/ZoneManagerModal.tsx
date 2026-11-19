import { useEffect, useState } from "react";
import type { Zone } from "../types";
import { createZone, deleteZone, listZones, updateZone } from "../api/client";

interface ZoneManagerModalProps {
  onClose: () => void;
}

/** Split free text ("1082, 1083 1084") into postal codes. */
function parseZips(text: string): string[] {
  return text.split(/[\s,;]+/).filter(Boolean);
}

function errorText(err: unknown): string {
  const data = (err as { response?: { data?: { error?: string } } })?.response?.data;
  return data?.error || "Could not save the zone.";
}

/**
 * Planner-defined zones: postal codes that travel together. The zip-atomic split keeps a zone
 * on one biker when it fits and breaks up as few zones as possible when it doesn't.
 */
export function ZoneManagerModal({ onClose }: ZoneManagerModalProps) {
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [name, setName] = useState("");
  const [zipText, setZipText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listZones()
      .then((z) => {
        if (!cancelled) setZones(z);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load zones.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const startEdit = (zone: Zone | null) => {
    setError(null);
    setEditing(zone ? zone.id : "new");
    setName(zone?.name ?? "");
    setZipText(zone ? zone.zips.join(", ") : "");
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    const body = { name: name.trim(), zips: parseZips(zipText) };
    try {
      if (editing === "new") {
        const created = await createZone(body);
        setZones((prev) => [...(prev ?? []), created]);
      } else if (editing) {
        const updated = await updateZone(editing, body);
        setZones((prev) => (prev ?? []).map((z) => (z.id === updated.id ? updated : z)));
      }
      setEditing(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (zone: Zone) => {
    setBusy(true);
    setError(null);
    try {
      await deleteZone(zone.id);
      setZones((prev) => (prev ?? []).filter((z) => z.id !== zone.id));
      if (editing === zone.id) setEditing(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const editor = (
    <div className="zone-editor" data-testid="zone-editor">
      <input
        type="text"
        value={name}
        placeholder="Name (optional)"
        aria-label="Zone name"
        onChange={(e) => setName(e.target.value)}
      />
      <input
        type="text"
        value={zipText}
        placeholder="Postal codes, e.g. 1082, 1083"
        aria-label="Zone postal codes"
        autoFocus
        onChange={(e) => setZipText(e.target.value)}
      />
      <div className="zone-editor-actions">
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(null)} disabled={busy}>
          Cancel
        </button>
        <button className="btn btn-primary btn-sm" onClick={save} disabled={busy || parseZips(zipText).length === 0}>
          Save zone
        </button>
      </div>
    </div>
  );

  return (
    <div className="move-stop-overlay" onClick={onClose}>
      <div className="move-stop-card zone-manager" role="dialog" aria-label="Zones" onClick={(e) => e.stopPropagation()}>
        <h2>Zones</h2>
        <p className="zone-manager-hint">
          Postal codes in one zone are planned together. When you split a day, whole zones go to a biker; a zone is only
          broken up when it has to be. Postal codes in no zone are planned on their own.
        </p>
        {error && (
          <div className="split-planner-error" role="alert">
            <span>{error}</span>
          </div>
        )}
        {zones === null && !error && <p>Loading…</p>}
        <ul className="zone-list">
          {(zones ?? []).map((zone) => (
            <li key={zone.id} className="zone-item" data-testid="zone-item">
              {editing === zone.id ? (
                editor
              ) : (
                <>
                  <div className="zone-item-main">
                    <b>{zone.name || zone.id}</b>
                    <span className="zone-item-id">{zone.id}</span>
                    <span className="zone-item-zips">
                      {zone.zips.map((z) => (
                        <span key={z} className="zone-chip">
                          {z}
                        </span>
                      ))}
                    </span>
                  </div>
                  <div className="zone-item-actions">
                    <button className="btn btn-ghost btn-sm" onClick={() => startEdit(zone)} disabled={busy}>
                      Edit
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => remove(zone)}
                      disabled={busy}
                      aria-label={`Delete zone ${zone.name || zone.id}`}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
        {editing === "new" ? (
          editor
        ) : (
          <button className="btn btn-primary btn-sm" onClick={() => startEdit(null)} disabled={zones === null}>
            + Add zone
          </button>
        )}
        <button className="btn btn-ghost" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
