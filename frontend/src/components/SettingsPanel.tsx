import { useState } from "react";
import type { DeliverySettings } from "../hooks/useSettings";

interface SettingsPanelProps {
  settings: DeliverySettings;
  onUpdate: (partial: Partial<DeliverySettings>) => void;
  isOpen: boolean;
  onClose: () => void;
}

const SPEED_PRESETS = [
  { label: "Walk", speed: 5, icon: "walk" },
  { label: "Bike", speed: 15, icon: "bike" },
  { label: "Car", speed: 40, icon: "car" },
] as const;

function WalkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="4" r="2" />
      <path d="M14 7l-2 9-2-4-3 5" />
      <path d="M10 16l-1 4" />
      <path d="M14 7l3 5" />
    </svg>
  );
}

function BikeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5.5" cy="17.5" r="3.5" />
      <circle cx="18.5" cy="17.5" r="3.5" />
      <path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2z" fill="currentColor" />
      <path d="M12 17.5V14l-3-3 4-3 2 3h3" />
    </svg>
  );
}

function CarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 17h14v-5l-2-5H7L5 12v5z" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
      <path d="M5 12h14" />
    </svg>
  );
}

function SpeedIcon({ type }: { type: string }) {
  switch (type) {
    case "walk": return <WalkIcon />;
    case "bike": return <BikeIcon />;
    case "car": return <CarIcon />;
    default: return null;
  }
}

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

export function SettingsPanel({ settings, onUpdate, isOpen, onClose }: SettingsPanelProps) {
  const [homeInput, setHomeInput] = useState(settings.homeAddress);
  const [isGeocodingHome, setIsGeocodingHome] = useState(false);
  const [homeError, setHomeError] = useState("");

  if (!isOpen) return null;

  const activePreset = SPEED_PRESETS.find((p) => p.speed === settings.speedKmh);
  const hasHome = settings.homeLat != null && settings.homeLng != null;

  async function geocodeHome() {
    if (!homeInput.trim()) return;
    setIsGeocodingHome(true);
    setHomeError("");
    try {
      const res = await fetch(
        `${NOMINATIM_URL}?${new URLSearchParams({ q: homeInput.trim(), format: "jsonv2", limit: "1" })}`,
        { headers: { "User-Agent": "DeliveryRoutePlanner/1.0" } }
      );
      const results = await res.json();
      if (results.length === 0) {
        setHomeError("Address not found");
        return;
      }
      onUpdate({
        homeAddress: homeInput.trim(),
        homeLat: parseFloat(results[0].lat),
        homeLng: parseFloat(results[0].lon),
      });
      setHomeError("");
    } catch {
      setHomeError("Geocoding failed");
    } finally {
      setIsGeocodingHome(false);
    }
  }

  function clearHome() {
    setHomeInput("");
    setHomeError("");
    onUpdate({ homeAddress: "", homeLat: null, homeLng: null });
  }

  return (
    <div className="settings-panel">
      <div className="settings-header">
        <h3>Route Settings</h3>
        <button className="stop-detail-close" onClick={onClose} aria-label="Close settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="settings-body">
        {/* Home / Depot */}
        <div className="setting-group">
          <label className="setting-label">
            <span>Home / Depot</span>
            {hasHome && <span className="setting-value-badge">Set</span>}
          </label>
          <p className="setting-hint">Route will start and return here</p>
          {hasHome ? (
            <div className="home-set">
              <div className="home-set-info">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9 22 9 12 15 12 15 22" />
                </svg>
                <div>
                  <span className="home-set-address">{settings.homeAddress}</span>
                  <span className="home-set-coords">
                    {settings.homeLat!.toFixed(4)}, {settings.homeLng!.toFixed(4)}
                  </span>
                </div>
              </div>
              <button className="home-clear" onClick={clearHome} title="Remove home location">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          ) : (
            <div className="home-input-row">
              <input
                type="text"
                className="setting-input home-input"
                placeholder="Enter address..."
                value={homeInput}
                onChange={(e) => setHomeInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") geocodeHome(); }}
              />
              <button
                className="btn btn-primary home-geocode-btn"
                onClick={geocodeHome}
                disabled={isGeocodingHome || !homeInput.trim()}
              >
                {isGeocodingHome ? (
                  <span className="upload-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                )}
              </button>
            </div>
          )}
          {homeError && <span className="setting-error">{homeError}</span>}
        </div>

        {/* Start Time */}
        <div className="setting-group">
          <label className="setting-label">Start Time</label>
          <input
            type="time"
            className="setting-input"
            value={settings.startTime}
            onChange={(e) => onUpdate({ startTime: e.target.value })}
          />
        </div>

        {/* Dwell Time */}
        <div className="setting-group">
          <label className="setting-label">
            Time at each stop
            <span className="setting-value-badge">{settings.dwellMinutes} min</span>
          </label>
          <input
            type="range"
            className="setting-slider"
            min={0}
            max={15}
            step={1}
            value={settings.dwellMinutes}
            onChange={(e) => onUpdate({ dwellMinutes: Number(e.target.value) })}
          />
          <div className="setting-range-labels">
            <span>0 min</span>
            <span>15 min</span>
          </div>
        </div>

        {/* Travel Speed */}
        <div className="setting-group">
          <label className="setting-label">Travel Speed</label>
          <div className="speed-presets">
            {SPEED_PRESETS.map((preset) => (
              <button
                key={preset.icon}
                className={`speed-preset ${activePreset?.icon === preset.icon ? "speed-preset--active" : ""}`}
                onClick={() => onUpdate({ speedKmh: preset.speed })}
                title={`${preset.label} (${preset.speed} km/h)`}
              >
                <SpeedIcon type={preset.icon} />
                <span className="speed-preset-label">{preset.label}</span>
                <span className="speed-preset-speed">{preset.speed} km/h</span>
              </button>
            ))}
          </div>
          <div className="speed-custom">
            <label className="setting-label">
              Custom speed
              <span className="setting-value-badge">{settings.speedKmh} km/h</span>
            </label>
            <input
              type="range"
              className="setting-slider"
              min={3}
              max={60}
              step={1}
              value={settings.speedKmh}
              onChange={(e) => onUpdate({ speedKmh: Number(e.target.value) })}
            />
            <div className="setting-range-labels">
              <span>3 km/h</span>
              <span>60 km/h</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
