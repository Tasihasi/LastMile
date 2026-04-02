import { useState } from "react";
import type { DeliveryStop } from "../types";

interface StopDetailProps {
  stop: DeliveryStop;
  onClose: () => void;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <button
      className="copy-btn"
      onClick={handleCopy}
      title="Copy to clipboard"
      aria-label="Copy phone number"
    >
      {copied ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}

export function StopDetail({ stop, onClose }: StopDetailProps) {
  const hasDetails = stop.product_code || stop.recipient_name || stop.recipient_phone;

  return (
    <div className="stop-detail-overlay" onClick={onClose}>
      <div className="stop-detail" onClick={(e) => e.stopPropagation()}>
        <div className="stop-detail-header">
          <h3>{stop.name}</h3>
          <button className="stop-detail-close" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="stop-detail-body">
          {stop.raw_address && (
            <div className="detail-row">
              <span className="detail-label">Address</span>
              <span className="detail-value">{stop.raw_address}</span>
            </div>
          )}
          {stop.lat != null && stop.lng != null && (
            <div className="detail-row">
              <span className="detail-label">Coordinates</span>
              <span className="detail-value detail-mono">{stop.lat.toFixed(5)}, {stop.lng.toFixed(5)}</span>
            </div>
          )}

          {hasDetails && <div className="detail-divider" />}

          {stop.product_code && (
            <div className="detail-row">
              <span className="detail-label">Product Code</span>
              <span className="detail-value">
                <span className="detail-code">{stop.product_code}</span>
              </span>
            </div>
          )}
          {stop.recipient_name && (
            <div className="detail-row">
              <span className="detail-label">Recipient</span>
              <span className="detail-value">{stop.recipient_name}</span>
            </div>
          )}
          {stop.recipient_phone && (
            <div className="detail-row">
              <span className="detail-label">Phone</span>
              <span className="detail-value detail-phone">
                <a href={`tel:${stop.recipient_phone}`}>{stop.recipient_phone}</a>
                <CopyButton text={stop.recipient_phone} />
              </span>
            </div>
          )}

          <div className="detail-divider" />

          <div className="detail-row">
            <span className="detail-label">Status</span>
            <span className="detail-value">
              <span className={`stop-status stop-status--${stop.geocode_status}`}>
                {stop.geocode_status === "success" ? "Geocoded" : stop.geocode_status === "skipped" ? "Has coords" : stop.geocode_status === "failed" ? "Failed" : "Pending"}
              </span>
            </span>
          </div>
          {stop.sequence_order != null && (
            <div className="detail-row">
              <span className="detail-label">Route Order</span>
              <span className="detail-value detail-mono">#{stop.sequence_order}</span>
            </div>
          )}
          {stop.geocode_error && (
            <div className="detail-row">
              <span className="detail-label">Error</span>
              <span className="detail-value stop-error">{stop.geocode_error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
