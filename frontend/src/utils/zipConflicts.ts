import type { SessionResponse, ZipConflict } from "../types";

const ANY_ZIP = /(?<!\d)[1-9]\d{3}(?!\d)/;

/** Postal code of a stop: the stored field, else parsed from the address ("" if unknown). */
export function stopZip(stop: { postal_code: string; raw_address: string }): string {
  const stored = (stop.postal_code ?? "").trim();
  if (stored) return stored;
  return ANY_ZIP.exec(stop.raw_address ?? "")?.[0] ?? "";
}

/** Postal codes spread over more than one route. Mirrors backend find_zip_conflicts. */
export function findZipConflicts(
  routes: Pick<SessionResponse, "id" | "name" | "stops">[]
): ZipConflict[] {
  const byZip = new Map<string, Map<string, number>>();
  for (const route of routes) {
    for (const stop of route.stops) {
      if (stop.excluded) continue;
      const zip = stopZip(stop);
      if (!zip) continue;
      const counts = byZip.get(zip) ?? new Map<string, number>();
      counts.set(route.id, (counts.get(route.id) ?? 0) + 1);
      byZip.set(zip, counts);
    }
  }
  const names = new Map(routes.map((r) => [r.id, r.name]));
  return [...byZip.entries()]
    .filter(([, counts]) => counts.size > 1)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([zip, counts]) => ({
      zip,
      zone: null,
      routes: [...counts.entries()]
        .map(([session_id, count]) => ({ session_id, name: names.get(session_id) ?? "", count }))
        .sort((a, b) => a.name.localeCompare(b.name)),
    }));
}
