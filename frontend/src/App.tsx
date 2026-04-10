import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDeliveryPlanner } from "./hooks/useDeliveryPlanner";
import { useTheme } from "./hooks/useTheme";
import { useSettings } from "./hooks/useSettings";
import { useAuth } from "./hooks/useAuth";
import { useToast } from "./hooks/useToast";
import { FileUpload } from "./components/FileUpload";
import { AddressList } from "./components/AddressList";
import { DeliveryMap } from "./components/DeliveryMap";
import { StopDetail } from "./components/StopDetail";
import { SettingsPanel } from "./components/SettingsPanel";
import { LoginScreen } from "./components/LoginScreen";
import { SessionList } from "./components/SessionList";
import { PlannerDashboard } from "./components/PlannerDashboard";
import { PlannerMapView } from "./components/PlannerMapView";
import { shareSession } from "./api/client";
import { formatDuration, formatDistance, formatTime, calcArrivalTimes } from "./utils/format";
import "./App.css";

function App() {
  const navigate = useNavigate();
  const { user, logout, isPlanner } = useAuth();
  const {
    sessionId,
    stops,
    needsGeocoding,
    isUploading,
    isGeocoding,
    geocodeProgress,
    isOptimizing,
    routeGeometry,
    routeSegments,
    totalDistance,
    error,
    sessionStatus,
    currentStopIndex,
    uploadFile,
    loadSession,
    geocode,
    optimize,
    startDeliveryRoute,
    markStop,
    reset,
  } = useDeliveryPlanner();

  const { theme, toggle: toggleTheme } = useTheme();
  const { settings, update: updateSettings } = useSettings();
  const { showToast } = useToast();
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [overflowMenuOpen, setOverflowMenuOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [viewMode, setViewMode] = useState<"dashboard" | "map" | "live-map">(isPlanner ? "dashboard" : "map");
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [confirmReoptimize, setConfirmReoptimize] = useState(false);

  // Sync view mode when user role changes (e.g. after login via UI)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (isPlanner && viewMode === "map" && stops.length === 0 && !showUpload) {
      setViewMode("dashboard");
    }
  }, [isPlanner]);

  // Close the header overflow menu when clicking outside of it.
  useEffect(() => {
    if (!overflowMenuOpen) return;
    const onDocClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".header-overflow")) {
        setOverflowMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [overflowMenuOpen]);

  const locatedCount = stops.filter(
    (s) => s.lat != null && s.lng != null
  ).length;
  const failedCount = stops.filter(
    (s) => s.geocode_status === "failed"
  ).length;
  const canOptimize = !needsGeocoding && !isGeocoding && locatedCount >= 2;
  const isOptimized = stops.some((s) => s.sequence_order != null);

  const selectStop = useCallback((id: number) => {
    setSelectedStopId(id);
    setSidebarOpen(false);
  }, []);

  const selectedStop = selectedStopId != null
    ? stops.find((s) => s.id === selectedStopId) ?? null
    : null;

  const hasDepot = settings.homeLat != null && settings.homeLng != null;
  const depot = hasDepot ? { lat: settings.homeLat!, lng: settings.homeLng!, address: settings.homeAddress } : null;

  const arrivalTimes = useMemo(() => {
    if (!routeSegments) return null;
    return calcArrivalTimes(routeSegments, settings, stops.length, hasDepot);
  }, [routeSegments, settings, stops.length, hasDepot]);

  const finishTime = useMemo(() => {
    if (!arrivalTimes) return null;
    if (hasDepot) {
      return arrivalTimes.get(-1) ?? null;
    }
    const lastOrder = stops.reduce((max, s) => Math.max(max, s.sequence_order ?? 0), 0);
    const lastArrival = arrivalTimes.get(lastOrder);
    if (!lastArrival) return null;
    return new Date(lastArrival.getTime() + settings.dwellMinutes * 60 * 1000);
  }, [arrivalTimes, hasDepot, stops, settings.dwellMinutes]);

  const totalRouteTime = useMemo(() => {
    if (!arrivalTimes || !finishTime) return null;
    const startPoint = arrivalTimes.get(hasDepot ? 0 : 1);
    if (!startPoint) return null;
    return Math.round((finishTime.getTime() - startPoint.getTime()) / 1000);
  }, [arrivalTimes, finishTime, hasDepot]);

  const handleShare = async () => {
    if (!sessionId) return;
    setShareLoading(true);
    try {
      const shareId = await shareSession(sessionId);
      const url = `${window.location.origin}/shared/${shareId}`;
      await navigator.clipboard.writeText(url);
      setShareCopied(true);
      showToast("Share link copied to clipboard");
      setTimeout(() => setShareCopied(false), 2000);
    } catch {
      showToast("Failed to create share link", "error");
    } finally {
      setShareLoading(false);
    }
  };

  const handleStartOver = () => {
    reset();
    setShowUpload(false);
    if (isPlanner) setViewMode("dashboard");
  };

  const handleNewRoute = () => {
    reset();
    setShowUpload(true);
    setViewMode("map");
  };

  const handleSelectSession = (id: string) => {
    loadSession(id);
    setShowUpload(false);
    setViewMode("map");
  };

  // Show session list when no active session and not uploading (biker only)
  const showSessionList = !isPlanner && stops.length === 0 && !showUpload;

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-left">
          <div className="app-logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
            </svg>
          </div>
          <h1>LastMile</h1>
        </div>
        <div className="app-header-right">
          {isPlanner && viewMode === "map" && (
            <button className="btn btn-ghost" onClick={handleStartOver}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              Dashboard
            </button>
          )}
          {!isPlanner && showUpload && stops.length === 0 && (
            <button className="btn btn-ghost" onClick={() => setShowUpload(false)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              Back
            </button>
          )}
          {viewMode === "map" && stops.length > 0 && (
            <button
              className="sidebar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
              title="Toggle sidebar"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          )}
          {!isPlanner && stops.length > 0 && sessionStatus === "not_started" && (
            <button
              className="btn btn-ghost btn-ghost--start-over"
              onClick={handleStartOver}
              aria-label="Start over — clear current route"
              title="Start Over"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              <span className="btn-ghost--start-over-label">Start Over</span>
            </button>
          )}
          {stops.length > 0 && (
            <button
              className={`theme-toggle ${settingsOpen ? "theme-toggle--active" : ""}`}
              onClick={() => {
                setSettingsOpen((open) => !open);
                // On mobile the sidebar can be hidden — ensure the settings
                // panel becomes visible when opened.
                if (!settingsOpen) setSidebarOpen(true);
              }}
              aria-label="Route settings"
              title="Route settings"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          )}
          <div className={`header-overflow ${overflowMenuOpen ? "header-overflow--open" : ""}`}>
            <button
              className="theme-toggle header-overflow-toggle"
              onClick={() => setOverflowMenuOpen((o) => !o)}
              aria-label="More options"
              aria-expanded={overflowMenuOpen}
              title="More"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="5" r="1" />
                <circle cx="12" cy="12" r="1" />
                <circle cx="12" cy="19" r="1" />
              </svg>
            </button>
            <div className="header-overflow-items">
              <button
                className="theme-toggle"
                onClick={() => { setOverflowMenuOpen(false); navigate("/docs"); }}
                aria-label="Help & Documentation"
                title="Help & Documentation"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </button>
              <button
                className="theme-toggle"
                onClick={() => { setOverflowMenuOpen(false); toggleTheme(); }}
                aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
                title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              >
                {theme === "light" ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                )}
              </button>
              <button
                className="btn btn-ghost user-badge"
                onClick={() => { setOverflowMenuOpen(false); logout(); }}
                aria-label={`Sign out ${user.username}`}
                title="Sign out"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span className="user-badge-name">{user.username}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {isPlanner && viewMode === "dashboard" ? (
        <PlannerDashboard
          onViewSession={handleSelectSession}
          onOpenLiveMap={() => setViewMode("live-map")}
          onOpenMapView={handleNewRoute}
        />
      ) : isPlanner && viewMode === "live-map" ? (
        <PlannerMapView onBack={() => setViewMode("dashboard")} onViewSession={handleSelectSession} />
      ) : (
      <>
      <div className="app-layout">
        {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
        <aside className={`sidebar ${sidebarOpen || showSessionList || (showUpload && stops.length === 0) ? "sidebar--open" : ""}`}>
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

            <SettingsPanel
              settings={settings}
              onUpdate={updateSettings}
              isOpen={settingsOpen}
              onClose={() => setSettingsOpen(false)}
            />

            {showSessionList ? (
              <SessionList
                onSelectSession={handleSelectSession}
                onNewRoute={handleNewRoute}
              />
            ) : stops.length === 0 ? (
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

                {/* Route summary after optimization */}
                {totalRouteTime != null && totalDistance != null && finishTime && (
                  <div className="route-summary">
                    <div className="route-summary-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      <span>{formatDuration(totalRouteTime)}</span>
                    </div>
                    <div className="route-summary-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                        <circle cx="12" cy="10" r="3" />
                      </svg>
                      <span>{formatDistance(totalDistance)}</span>
                    </div>
                    <div className="route-summary-item">
                      <span className="route-summary-time">{settings.startTime} - {formatTime(finishTime)}</span>
                    </div>
                    <button
                      className="btn btn-ghost share-btn"
                      onClick={handleShare}
                      disabled={shareLoading}
                      title="Copy share link"
                    >
                      {shareCopied ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="18" cy="5" r="3" />
                          <circle cx="6" cy="12" r="3" />
                          <circle cx="18" cy="19" r="3" />
                          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                        </svg>
                      )}
                      {shareCopied ? "Copied!" : "Share"}
                    </button>
                  </div>
                )}

                {/* Geocode progress bar */}
                {isGeocoding && geocodeProgress && (
                  <GeocodeProgress progress={geocodeProgress} />
                )}

                {/* Route status banner */}
                {sessionStatus === "in_progress" && (
                  <div className="route-status-banner route-status-banner--active">
                    <span className="route-status-dot" />
                    Route in progress — {stops.filter(s => s.delivery_status !== "pending").length}/{stops.length} stops done
                  </div>
                )}
                {sessionStatus === "finished" && (
                  <div className="route-status-banner route-status-banner--finished">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                    Route completed
                  </div>
                )}

                {/* Action buttons */}
                <div className="sidebar-actions">
                  {/* Start Route — only for bikers with optimized, not-started routes */}
                  {isOptimized && sessionStatus === "not_started" && !isPlanner && (
                    <button
                      className="btn btn-start-route"
                      onClick={startDeliveryRoute}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      Start Route
                    </button>
                  )}
                  {needsGeocoding && sessionStatus === "not_started" && (
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
                  {canOptimize && sessionStatus === "not_started" && (
                    <button
                      className="btn btn-primary"
                      onClick={() => optimize(
                        settings.homeLat != null && settings.homeLng != null
                          ? { lat: settings.homeLat, lng: settings.homeLng }
                          : null
                      )}
                      disabled={isOptimizing}
                      style={!isOptimized ? { background: "var(--color-accent)" } : undefined}
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
                          {isOptimized ? "Re-optimize" : "Optimize Route"}
                        </>
                      )}
                    </button>
                  )}
                  {canOptimize && isOptimized && sessionStatus === "in_progress" && (
                    confirmReoptimize ? (
                      <div className="reoptimize-confirm">
                        <span>Re-optimize will change the route order. Continue?</span>
                        <div className="reoptimize-confirm-actions">
                          <button className="btn btn-sm btn-ghost" onClick={() => setConfirmReoptimize(false)}>Cancel</button>
                          <button
                            className="btn btn-sm btn-primary"
                            disabled={isOptimizing}
                            onClick={() => {
                              setConfirmReoptimize(false);
                              optimize(
                                settings.homeLat != null && settings.homeLng != null
                                  ? { lat: settings.homeLat, lng: settings.homeLng }
                                  : null
                              );
                            }}
                          >
                            {isOptimizing ? "Optimizing..." : "Re-optimize"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setConfirmReoptimize(true)}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                        Re-optimize Route
                      </button>
                    )
                  )}
                </div>

                <AddressList
                  stops={stops}
                  selectedStopId={selectedStopId}
                  onSelectStop={selectStop}
                  routeSegments={routeSegments}
                  arrivalTimes={arrivalTimes}
                  speedKmh={settings.speedKmh}
                  depot={depot}
                  sessionStatus={sessionStatus}
                  currentStopIndex={currentStopIndex}
                  onMarkStop={markStop}
                />
              </>
            )}
          </div>
        </aside>

        <main className="map-container">
          <DeliveryMap
            stops={stops}
            routeGeometry={routeGeometry}
            onSelectStop={selectStop}
            depot={depot}
            sessionStatus={sessionStatus}
            currentStopIndex={currentStopIndex}
          />
        </main>
      </div>

      {selectedStop && (
        <StopDetail
          stop={selectedStop}
          onClose={() => setSelectedStopId(null)}
          routeSegments={routeSegments}
          stops={stops}
          arrivalTimes={arrivalTimes}
          speedKmh={settings.speedKmh}
        />
      )}
      </>
      )}
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
