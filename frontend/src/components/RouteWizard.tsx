import { HoldToConfirmButton } from "./HoldToConfirmButton";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DeliveryStop } from "../types";

import { fileKey, type WizardStep } from "../utils/wizard";
import { WizardFooter } from "./WizardFooter";
import { PostalCodeStep, type StopPatch } from "./PostalCodeStep";

const STEPS: { step: WizardStep; label: string }[] = [
  { step: 1, label: "Upload" },
  { step: 2, label: "Geocode" },
  { step: 3, label: "Fix addresses" },
  { step: 4, label: "Postal codes" },
  { step: 5, label: "Optimize" },
];

const ACCEPTED = ".csv,.xlsx,.txt,.xml";
const FORMATS = ["csv", "xlsx", "txt", "xml"];

interface StepperProps {
  current: WizardStep;
  /** Highest step the user may jump to right now. */
  maxStep: WizardStep;
  disabled?: boolean;
  /** Planners distribute the route between bikers in the last step. */
  planner?: boolean;
  /** Lowest step that can be revisited (an existing route has no files to re-pick). */
  minStep?: WizardStep;
  onStepChange: (step: WizardStep) => void;
}

export function WizardStepper({ current, maxStep, disabled, planner, minStep = 1, onStepChange }: StepperProps) {
  return (
    <nav className="wizard-stepper" aria-label="Route planning steps">
      {STEPS.map(({ step, label }) => {
        const state = step === current ? "current" : step < current ? "done" : "todo";
        return (
          <button
            key={step}
            type="button"
            className={`wizard-step wizard-step--${state}`}
            disabled={disabled || step > maxStep || step < minStep}
            aria-current={step === current ? "step" : undefined}
            onClick={() => onStepChange(step)}
          >
            <span className="wizard-step-num">{state === "done" ? "✓" : step}</span>
            <span className="wizard-step-label">{planner && step === 5 ? "Bikers" : label}</span>
          </button>
        );
      })}
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* Step 1 — upload one or more files                                   */
/* ------------------------------------------------------------------ */

interface UploadStepProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  isUploading: boolean;
  onNext: () => void;
  onCancel: () => void;
}

function UploadStep({ files, onFilesChange, isUploading, onNext, onCancel }: UploadStepProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const known = new Set(files.map(fileKey));
      const fresh = Array.from(incoming).filter((f) => !known.has(fileKey(f)));
      if (fresh.length) onFilesChange([...files, ...fresh]);
    },
    [files, onFilesChange]
  );

  return (
    <section className="wizard-card">
      <h2 className="wizard-title">Upload your delivery files</h2>
      <p className="wizard-sub">
        Add one or more files — all of their stops are combined into a single route.
      </p>

      <div
        className={`file-upload wizard-dropzone ${isDragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            if (inputRef.current) inputRef.current.value = "";
          }}
        />
        <div className="upload-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <p className="upload-title">{files.length ? "Add more files" : "Drop your files here"}</p>
        <p className="upload-subtitle">or click to browse</p>
        <div className="upload-formats">
          {FORMATS.map((f) => (
            <span key={f} className="upload-format-tag">.{f}</span>
          ))}
        </div>
      </div>

      {files.length > 0 && (
        <ul className="wizard-file-list">
          {files.map((f) => (
            <li key={fileKey(f)} className="wizard-file">
              <span className="wizard-file-name">{f.name}</span>
              <span className="wizard-file-size">{Math.max(1, Math.round(f.size / 1024))} KB</span>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                aria-label={`Remove ${f.name}`}
                onClick={() => onFilesChange(files.filter((x) => x !== f))}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <WizardFooter
        onBack={onCancel}
        backLabel="Cancel"
        onNext={onNext}
        nextLabel={isUploading ? "Processing…" : "Upload & continue"}
        nextDisabled={files.length === 0}
        busy={isUploading}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Step 2 — geocode                                                    */
/* ------------------------------------------------------------------ */

interface GeocodeStepProps {
  stops: DeliveryStop[];
  needsGeocoding: boolean;
  isGeocoding: boolean;
  progress: string;
  onGeocode: () => void;
  onBack: () => void;
  onNext: () => void;
}

function GeocodeStep({ stops, needsGeocoding, isGeocoding, progress, onGeocode, onBack, onNext }: GeocodeStepProps) {
  const located = stops.filter((s) => s.lat != null && s.lng != null).length;
  const failed = stops.filter((s) => s.geocode_status === "failed").length;
  const pending = stops.filter((s) => s.geocode_status === "pending").length;

  // Kick geocoding off once on entering the step; afterwards a failure is
  // retried only through the explicit button, so an error can't loop.
  const autoStarted = useRef(false);
  useEffect(() => {
    if (autoStarted.current || !needsGeocoding || isGeocoding) return;
    autoStarted.current = true;
    onGeocode();
  }, [needsGeocoding, isGeocoding, onGeocode]);

  const match = progress.match(/(\d+)\/(\d+)/);
  const pct = match ? Math.round((parseInt(match[1]) / parseInt(match[2])) * 100) : 0;

  return (
    <section className="wizard-card">
      <h2 className="wizard-title">Finding coordinates</h2>
      <p className="wizard-sub">Each address is looked up on the map. This takes about a second per stop.</p>

      <div className="wizard-stats">
        <div className="wizard-stat"><strong>{stops.length}</strong><span>Stops</span></div>
        <div className="wizard-stat wizard-stat--ok"><strong>{located}</strong><span>Located</span></div>
        <div className={`wizard-stat ${failed ? "wizard-stat--bad" : ""}`}><strong>{failed}</strong><span>Not found</span></div>
        {pending > 0 && <div className="wizard-stat"><strong>{pending}</strong><span>Waiting</span></div>}
      </div>

      {isGeocoding && (
        <div className="progress-section">
          <div className="progress-label">
            <span>{progress || "Starting…"}</span>
            <span>{pct}%</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {!isGeocoding && needsGeocoding && (
        <button type="button" className="btn btn-primary" onClick={onGeocode}>
          Retry geocoding
        </button>
      )}

      {!isGeocoding && !needsGeocoding && (
        <p className={`wizard-result ${failed ? "wizard-result--warn" : "wizard-result--ok"}`}>
          {failed
            ? `${failed} address${failed === 1 ? "" : "es"} could not be found — you can correct ${failed === 1 ? "it" : "them"} in the next step.`
            : "All addresses were located."}
        </p>
      )}

      <WizardFooter
        onBack={onBack}
        backLabel="Files"
        onNext={onNext}
        nextLabel={failed ? "Fix addresses" : "Review addresses"}
        nextDisabled={needsGeocoding}
        busy={isGeocoding}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Step 3 — fix addresses that could not be found                      */
/* ------------------------------------------------------------------ */

interface FixStepProps {
  stops: DeliveryStop[];
  canRemove: boolean;
  onFixAddress: (stopId: number, address: string) => Promise<boolean>;
  onRemoveStop: (stopId: number) => Promise<void>;
  onBack: () => void;
  onNext: () => void;
}

function FixRow({
  stop,
  canRemove,
  onFixAddress,
  onRemoveStop,
}: {
  stop: DeliveryStop;
  canRemove: boolean;
  onFixAddress: FixStepProps["onFixAddress"];
  onRemoveStop: FixStepProps["onRemoveStop"];
}) {
  const [draft, setDraft] = useState(stop.raw_address);
  const [busy, setBusy] = useState(false);
  const [tried, setTried] = useState(false);

  const submit = async () => {
    if (!draft.trim() || busy) return;
    setBusy(true);
    try {
      await onFixAddress(stop.id, draft.trim());
      setTried(true);
    } finally {
      setBusy(false);
    }
  };

  const ok = stop.geocode_status === "success";
  return (
    <li className={`fix-row ${ok ? "fix-row--ok" : ""}`}>
      <div className="fix-row-head">
        <strong>{stop.name}</strong>
        {stop.recipient_name && <span className="fix-row-meta">{stop.recipient_name}</span>}
        {ok && <span className="fix-row-badge">✓ Located</span>}
      </div>
      <form
        className="fix-row-form"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <input
          className="fix-row-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          aria-label={`Address for ${stop.name}`}
          placeholder="Street, number, city"
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !draft.trim()}>
          {busy ? "Searching…" : ok ? "Re-check" : "Find"}
        </button>
        {canRemove && !ok && (
          <HoldToConfirmButton
            className="btn btn-ghost btn-sm"
            disabled={busy}
            title="Hold to remove this stop"
            onConfirm={() => void onRemoveStop(stop.id)}
          >
            Remove
          </HoldToConfirmButton>
        )}
      </form>
      {!ok && tried && <p className="fix-row-error">Still not found — try adding the city or fixing the spelling.</p>}
    </li>
  );
}

function FixStep({ stops, canRemove, onFixAddress, onRemoveStop, onBack, onNext }: FixStepProps) {
  // Rows stay on screen after being fixed (so the user sees the ✓); a stop that
  // was never in a failed state is not listed. Track ids that have ever failed.
  const [everFailed, setEverFailed] = useState<Set<number>>(new Set());
  useEffect(() => {
    const failedNow = stops.filter((s) => s.geocode_status === "failed").map((s) => s.id);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (failedNow.some((id) => !everFailed.has(id))) setEverFailed((prev) => new Set([...prev, ...failedNow]));
  }, [stops, everFailed]);

  const rows = stops.filter((s) => everFailed.has(s.id) || s.geocode_status === "failed");
  const stillFailed = rows.filter((s) => s.geocode_status !== "success").length;
  const located = stops.filter((s) => s.lat != null && s.lng != null).length;

  return (
    <section className="wizard-card">
      <h2 className="wizard-title">Fix addresses</h2>
      {rows.length === 0 ? (
        <p className="wizard-result wizard-result--ok">Every address was found — nothing to fix.</p>
      ) : (
        <>
          <p className="wizard-sub">
            The recipient may have mistyped the address. Correct it and search again
            {stillFailed > 0 ? ` — ${stillFailed} left.` : " — all fixed."}
          </p>
          <ul className="fix-list">
            {rows.map((s) => (
              <FixRow key={s.id} stop={s} canRemove={canRemove} onFixAddress={onFixAddress} onRemoveStop={onRemoveStop} />
            ))}
          </ul>
        </>
      )}

      <WizardFooter
        onBack={onBack}
        backLabel="Geocoding"
        onNext={onNext}
        nextLabel={stillFailed ? "Continue without them" : "Continue"}
        nextDisabled={located < 2}
        hint={located < 2 ? "At least 2 located stops are needed" : undefined}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */

interface RouteWizardProps {
  step: WizardStep;
  files: File[];
  onFilesChange: (files: File[]) => void;
  isUploading: boolean;
  stops: DeliveryStop[];
  needsGeocoding: boolean;
  isGeocoding: boolean;
  geocodeProgress: string;
  error: string | null;
  canRemoveStops: boolean;
  onGeocode: () => void;
  onFixAddress: (stopId: number, address: string) => Promise<boolean>;
  onUpdateStops: (ids: number[], patch: StopPatch) => Promise<void>;
  onRemoveStop: (stopId: number) => Promise<void>;
  onStepChange: (step: WizardStep) => void;
  onCancel: () => void;
}

export function RouteWizard(props: RouteWizardProps) {
  const { step, error, onStepChange } = props;
  return (
    <div className="wizard-body">
      {error && <div className="error-banner wizard-error"><span>{error}</span></div>}
      {step === 1 && (
        <UploadStep
          files={props.files}
          onFilesChange={props.onFilesChange}
          isUploading={props.isUploading}
          onNext={() => onStepChange(2)}
          onCancel={props.onCancel}
        />
      )}
      {step === 2 && (
        <GeocodeStep
          stops={props.stops}
          needsGeocoding={props.needsGeocoding}
          isGeocoding={props.isGeocoding}
          progress={props.geocodeProgress}
          onGeocode={props.onGeocode}
          onBack={() => onStepChange(1)}
          onNext={() => onStepChange(3)}
        />
      )}
      {step === 3 && (
        <FixStep
          stops={props.stops}
          canRemove={props.canRemoveStops}
          onFixAddress={props.onFixAddress}
          onRemoveStop={props.onRemoveStop}
          onBack={() => onStepChange(2)}
          onNext={() => onStepChange(4)}
        />
      )}
      {step === 4 && (
        <PostalCodeStep
          stops={props.stops}
          onUpdateStops={props.onUpdateStops}
          onBack={() => onStepChange(3)}
          onNext={() => onStepChange(5)}
        />
      )}
    </div>
  );
}
