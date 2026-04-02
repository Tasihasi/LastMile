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

export function SettingsPanel({ settings, onUpdate, isOpen, onClose }: SettingsPanelProps) {
  if (!isOpen) return null;

  const activePreset = SPEED_PRESETS.find((p) => p.speed === settings.speedKmh);

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
