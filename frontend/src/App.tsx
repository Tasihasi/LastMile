import { useDeliveryPlanner } from "./hooks/useDeliveryPlanner";
import { FileUpload } from "./components/FileUpload";
import { AddressList } from "./components/AddressList";
import { DeliveryMap } from "./components/DeliveryMap";
import "./App.css";

function App() {
  const {
    stops,
    needsGeocoding,
    isUploading,
    isGeocoding,
    geocodeProgress,
    isOptimizing,
    routeGeometry,
    error,
    uploadFile,
    geocode,
    optimize,
    reset,
  } = useDeliveryPlanner();

  const locatedCount = stops.filter(
    (s) => s.lat != null && s.lng != null
  ).length;
  const failedCount = stops.filter(
    (s) => s.geocode_status === "failed"
  ).length;
  const canOptimize = !needsGeocoding && !isGeocoding && locatedCount >= 2;
  const isOptimized = stops.some((s) => s.sequence_order != null);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-left">
          <div className="app-logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
            </svg>
          </div>
          <h1>Route Planner</h1>
        </div>
        {stops.length > 0 && (
          <button className="btn btn-ghost" onClick={reset}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            Start Over
          </button>
        )}
      </header>

      <div className="app-layout">
        <aside className="sidebar">
          <div className="sidebar-content">
            {error && (
              <div className="error-banner">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {stops.length === 0 ? (
              <FileUpload onUpload={uploadFile} isUploading={isUploading} />
            ) : (
              <>
                {/* Stats */}
                <div className="stats-bar">
                  <div className="stat-item">
                    <div className="stat-value">{stops.length}</div>
                    <div className="stat-label">Total</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{locatedCount}</div>
                    <div className="stat-label">Located</div>
                  </div>
                  {failedCount > 0 && (
                    <div className="stat-item">
                      <div className="stat-value">{failedCount}</div>
                      <div className="stat-label">Failed</div>
                    </div>
                  )}
                </div>

                {/* Geocode progress bar */}
                {isGeocoding && geocodeProgress && (
                  <GeocodeProgress progress={geocodeProgress} />
                )}

                {/* Action buttons */}
                <div className="sidebar-actions">
                  {needsGeocoding && (
                    <button
                      className="btn btn-primary"
                      onClick={geocode}
                      disabled={isGeocoding}
                    >
                      {isGeocoding ? (
                        <>
                          <span className="upload-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                          Geocoding...
                        </>
                      ) : (
                        <>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                            <circle cx="12" cy="10" r="3" />
                          </svg>
                          Geocode Addresses
                        </>
                      )}
                    </button>
                  )}
                  {canOptimize && (
                    <button
                      className="btn btn-primary"
                      onClick={optimize}
                      disabled={isOptimizing}
                      style={isOptimized ? undefined : { background: "var(--color-accent)" }}
                    >
                      {isOptimizing ? (
                        <>
                          <span className="upload-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                          Optimizing...
                        </>
                      ) : (
                        <>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                          </svg>
                          {isOptimized ? "Re-optimize Route" : "Optimize Route"}
                        </>
                      )}
                    </button>
                  )}
                </div>

                <AddressList stops={stops} />
              </>
            )}
          </div>
        </aside>

        <main className="map-container">
          <DeliveryMap stops={stops} routeGeometry={routeGeometry} />
        </main>
      </div>
    </div>
  );
}

function GeocodeProgress({ progress }: { progress: string }) {
  const match = progress.match(/(\d+)\/(\d+)/);
  const current = match ? parseInt(match[1]) : 0;
  const total = match ? parseInt(match[2]) : 1;
  const pct = Math.round((current / total) * 100);

  return (
    <div className="progress-section">
      <div className="progress-label">
        <span>{progress}</span>
        <span>{pct}%</span>
      </div>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default App;
