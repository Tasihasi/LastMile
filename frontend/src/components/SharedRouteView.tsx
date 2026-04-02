import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedRoute } from "../api/client";
import type { SharedRouteResponse } from "../types";
import { DeliveryMap } from "./DeliveryMap";
import { AddressList } from "./AddressList";

export function SharedRouteView() {
  const { shareId } = useParams<{ shareId: string }>();
  const [data, setData] = useState<SharedRouteResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!shareId) return;
    getSharedRoute(shareId)
      .then(setData)
      .catch(() => setError("Route not found or link has expired."))
      .finally(() => setLoading(false));
  }, [shareId]);

  if (loading) {
    return (
      <div className="shared-route-loading">
        <span className="upload-spinner" />
        <p>Loading route...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="shared-route-error">
        <div className="app-logo">
          <svg viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
          </svg>
        </div>
        <h2>Route Not Found</h2>
        <p>{error || "This shared route doesn't exist."}</p>
      </div>
    );
  }

  const { session } = data;
  const stops = session.stops;

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-left">
          <div className="app-logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
            </svg>
          </div>
          <h1>Shared Route</h1>
          <span className="shared-route-badge">View Only</span>
        </div>
      </header>

      <div className="app-layout">
        <aside className="sidebar sidebar--open">
          <div className="sidebar-content">
            <AddressList
              stops={stops}
              selectedStopId={null}
              onSelectStop={() => {}}
              routeSegments={null}
              arrivalTimes={null}
              speedKmh={15}
              depot={null}
            />
          </div>
        </aside>

        <main className="map-container">
          <DeliveryMap
            stops={stops}
            routeGeometry={null}
            onSelectStop={() => {}}
            depot={null}
          />
        </main>
      </div>
    </div>
  );
}
