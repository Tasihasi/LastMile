import { useState } from "react";

interface RouteNameFieldProps {
  name: string;
  onSave: (name: string) => Promise<void> | void;
  /** Show just the pencil (the name is already displayed next to it). */
  iconOnly?: boolean;
}

/** Route name with an inline rename: click the pencil, Enter saves, Escape cancels. */
export function RouteNameField({ name, onSave, iconOnly = false }: RouteNameFieldProps) {
  const [draft, setDraft] = useState<string | null>(null);

  const commit = async () => {
    const next = (draft ?? "").trim();
    setDraft(null);
    if (next && next !== name) await onSave(next);
  };

  if (draft !== null) {
    return (
      <input
        className="route-name-input"
        value={draft}
        autoFocus
        maxLength={200}
        aria-label="Route name"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setDraft(null);
        }}
      />
    );
  }

  return (
    <button
      type="button"
      className="route-name"
      title="Rename route"
      aria-label={`Rename route ${name}`}
      onClick={() => setDraft(name)}
    >
      {!iconOnly && <span className="route-name-text">{name || "Untitled route"}</span>}
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
      </svg>
    </button>
  );
}
