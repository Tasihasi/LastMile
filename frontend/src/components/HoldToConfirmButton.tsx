import { useCallback, useEffect, useRef, useState } from "react";
import type { ButtonHTMLAttributes } from "react";
import { createPortal } from "react-dom";

/** How long the button must be held: long enough to reconsider, short enough not to nag. */
export const HOLD_TO_CONFIRM_MS = 1500;

interface HoldToConfirmButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onClick" | "onPointerDown"> {
  /** Runs once the button has been held for the full duration. */
  onConfirm: () => void;
  holdMs?: number;
}

/**
 * A destructive button that only fires when held down. While held, a rhombus
 * follows the cursor and a red line runs around it like a loader; letting go
 * early cancels.
 */
export function HoldToConfirmButton({
  onConfirm,
  holdMs = HOLD_TO_CONFIRM_MS,
  className = "",
  title,
  children,
  disabled,
  ...rest
}: HoldToConfirmButtonProps) {
  const [holding, setHolding] = useState(false);
  // The rhombus loader that follows the cursor; moved directly, not through state.
  const cursorRef = useRef<HTMLDivElement>(null);
  const pointerRef = useRef({ x: 0, y: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const timerRef = useRef<number | null>(null);
  const onConfirmRef = useRef(onConfirm);
  useEffect(() => {
    onConfirmRef.current = onConfirm;
  }, [onConfirm]);

  const cancel = useCallback(() => {
    if (timerRef.current != null) window.clearTimeout(timerRef.current);
    timerRef.current = null;
    setHolding(false);
  }, []);

  const start = useCallback((x?: number, y?: number) => {
    if (timerRef.current != null) return;
    const rect = buttonRef.current?.getBoundingClientRect();
    pointerRef.current = {
      x: x ?? (rect ? rect.left + rect.width / 2 : 0),
      y: y ?? (rect ? rect.top + rect.height / 2 : 0),
    };
    setHolding(true);
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      setHolding(false);
      onConfirmRef.current();
    }, holdMs);
  }, [holdMs]);

  useEffect(() => {
    if (!holding) return;
    const place = () => {
      const { x, y } = pointerRef.current;
      cursorRef.current?.style.setProperty("transform", `translate(${x}px, ${y}px)`);
    };
    const onMove = (e: PointerEvent) => {
      pointerRef.current = { x: e.clientX, y: e.clientY };
      place();
    };
    place();
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, [holding]);

  useEffect(
    () => () => {
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    },
    []
  );

  return (
    <button
      {...rest}
      ref={buttonRef}
      type="button"
      disabled={disabled}
      className={`hold-btn ${holding ? "hold-btn--holding" : ""} ${className}`}
      title={title ?? "Hold to confirm"}
      style={{ "--hold-ms": `${holdMs}ms` } as React.CSSProperties}
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        start(e.clientX, e.clientY);
      }}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={cancel}
      onBlur={cancel}
      onContextMenu={(e) => e.preventDefault()}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !e.repeat) {
          e.preventDefault();
          start();
        }
      }}
      onKeyUp={(e) => {
        if (e.key === "Enter" || e.key === " ") cancel();
      }}
    >
      {children}
      {holding &&
        createPortal(
          <div className="hold-cursor" ref={cursorRef} aria-hidden="true">
            <svg width="56" height="56" viewBox="0 0 56 56" style={{ "--hold-ms": `${holdMs}ms` } as React.CSSProperties}>
              <defs>
                <linearGradient id="hold-cursor-gradient" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#fb7185" />
                  <stop offset="100%" stopColor="#dc2626" />
                </linearGradient>
              </defs>
              <polygon className="hold-cursor-track" points="28,5 51,28 28,51 5,28" />
              <polygon className="hold-cursor-run" points="28,5 51,28 28,51 5,28" pathLength={1} />
              <circle className="hold-cursor-dot" cx="28" cy="28" r="3" />
            </svg>
          </div>,
          document.body
        )}
    </button>
  );
}
