import type { RouteSegment } from "../types";
import type { DeliverySettings } from "../hooks/useSettings";

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hours}h ${remainMins}m` : `${hours}h`;
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)} m`;
  const km = meters / 1000;
  return km >= 10 ? `${Math.round(km)} km` : `${km.toFixed(1)} km`;
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

/**
 * Calculate travel time in seconds for a segment using custom speed.
 * distance is in meters, speedKmh is in km/h.
 */
export function travelSeconds(distanceMeters: number, speedKmh: number): number {
  if (speedKmh <= 0) return 0;
  return Math.round(distanceMeters / (speedKmh / 3.6));
}

/**
 * Calculate arrival times for each stop based on settings.
 * Returns a Map from stop sequence_order to arrival Date.
 */
export function calcArrivalTimes(
  segments: RouteSegment[],
  settings: DeliverySettings,
  stopCount: number,
): Map<number, Date> {
  const arrivals = new Map<number, Date>();

  const [h, m] = settings.startTime.split(":").map(Number);
  const now = new Date();
  now.setHours(h, m, 0, 0);

  // Stop 1 = departure point, arrival = start time
  arrivals.set(1, new Date(now));

  let currentTime = now.getTime();

  for (let i = 0; i < segments.length && i < stopCount - 1; i++) {
    // Add dwell time at current stop (except first stop = depot, optional)
    currentTime += settings.dwellMinutes * 60 * 1000;
    // Add travel time to next stop
    const travel = travelSeconds(segments[i].distance, settings.speedKmh);
    currentTime += travel * 1000;
    arrivals.set(i + 2, new Date(currentTime));
  }

  return arrivals;
}
