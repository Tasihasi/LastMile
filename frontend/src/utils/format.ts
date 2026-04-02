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
 * Key 0 = depot departure, keys 1..N = delivery stops, key -1 = return home.
 *
 * When hasDepot=true, segments are: [depot->s1, s1->s2, ..., sN->depot]
 * When hasDepot=false, segments are: [s1->s2, s2->s3, ..., sN-1->sN]
 */
export function calcArrivalTimes(
  segments: RouteSegment[],
  settings: DeliverySettings,
  stopCount: number,
  hasDepot: boolean,
): Map<number, Date> {
  const arrivals = new Map<number, Date>();

  const [h, m] = settings.startTime.split(":").map(Number);
  const start = new Date();
  start.setHours(h, m, 0, 0);

  let currentTime = start.getTime();

  if (hasDepot) {
    // Segment 0 = depot -> first stop
    arrivals.set(0, new Date(currentTime)); // depot departure
    const depotToFirst = travelSeconds(segments[0].distance, settings.speedKmh);
    currentTime += depotToFirst * 1000;
    arrivals.set(1, new Date(currentTime)); // arrive at stop 1

    // Segments 1..stopCount-1 = between delivery stops
    for (let i = 1; i < segments.length - 1 && i < stopCount; i++) {
      currentTime += settings.dwellMinutes * 60 * 1000;
      const travel = travelSeconds(segments[i].distance, settings.speedKmh);
      currentTime += travel * 1000;
      arrivals.set(i + 1, new Date(currentTime));
    }

    // Last segment = last stop -> depot (return home)
    if (segments.length > stopCount) {
      currentTime += settings.dwellMinutes * 60 * 1000; // dwell at last stop
      const returnTravel = travelSeconds(segments[segments.length - 1].distance, settings.speedKmh);
      currentTime += returnTravel * 1000;
      arrivals.set(-1, new Date(currentTime)); // arrive home
    }
  } else {
    // No depot: stop 1 = start
    arrivals.set(1, new Date(currentTime));

    for (let i = 0; i < segments.length && i < stopCount - 1; i++) {
      currentTime += settings.dwellMinutes * 60 * 1000;
      const travel = travelSeconds(segments[i].distance, settings.speedKmh);
      currentTime += travel * 1000;
      arrivals.set(i + 2, new Date(currentTime));
    }
  }

  return arrivals;
}
