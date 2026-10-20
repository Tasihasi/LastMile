interface FooterProps {
  onBack?: () => void;
  backLabel?: string;
  onNext: () => void;
  nextLabel: string;
  nextDisabled?: boolean;
  busy?: boolean;
  hint?: string;
}

export function WizardFooter({ onBack, backLabel = "Back", onNext, nextLabel, nextDisabled, busy, hint }: FooterProps) {
  return (
    <div className="wizard-footer">
      {onBack ? (
        <button type="button" className="btn btn-ghost" onClick={onBack} disabled={busy}>
          ← {backLabel}
        </button>
      ) : (
        <span />
      )}
      <div className="wizard-footer-right">
        {hint && <span className="wizard-hint">{hint}</span>}
        <button type="button" className="btn btn-primary" onClick={onNext} disabled={nextDisabled || busy}>
          {nextLabel} →
        </button>
      </div>
    </div>
  );
}
