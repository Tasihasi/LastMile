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
  const canOptimize = !needsGeocoding && !isGeocoding && locatedCount >= 2;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Delivery Route Planner</h1>
        {stops.length > 0 && (
          <button className="btn btn-secondary" onClick={reset}>
            Start Over
          </button>
        )}
      </header>

      <div className="app-layout">
        <aside className="sidebar">
          {error && <div className="error-banner">{error}</div>}
          {stops.length === 0 ? (
            <FileUpload onUpload={uploadFile} isUploading={isUploading} />
          ) : (
            <>
              <div className="sidebar-actions">
                {needsGeocoding && (
                  <button
                    className="btn btn-primary"
                    onClick={geocode}
                    disabled={isGeocoding}
                  >
                    {isGeocoding ? geocodeProgress || "Geocoding..." : "Geocode Addresses"}
                  </button>
                )}
                {canOptimize && (
                  <button
                    className="btn btn-primary"
                    onClick={optimize}
                    disabled={isOptimizing}
                  >
                    {isOptimizing ? "Optimizing..." : "Optimize Route"}
                  </button>
                )}
              </div>
              <AddressList stops={stops} />
            </>
          )}
        </aside>

        <main className="map-container">
          <DeliveryMap stops={stops} routeGeometry={routeGeometry} />
        </main>
      </div>
    </div>
  );
}

export default App;
