import { useCallback, useEffect, useState } from "react";
import type { SessionResponse, User } from "../types";
import { getSession, listSessions, listBikers } from "../api/client";

/** Shared data loading for split-planner views: a parent session's sub-routes and the biker list. */
export function useSplitSubRoutes(parentSessionId: string) {
  const [subRoutes, setSubRoutes] = useState<SessionResponse[]>([]);
  const [parentSession, setParentSession] = useState<SessionResponse | null>(null);
  const [bikers, setBikers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [parent, sessionList, bikerList] = await Promise.all([
        getSession(parentSessionId),
        listSessions(undefined, parentSessionId),
        listBikers(),
      ]);
      setParentSession(parent);
      setBikers(bikerList);

      const childIds = sessionList.map((s) => s.id);

      const childSessions = await Promise.all(childIds.map((id) => getSession(id)));
      setSubRoutes(childSessions);
    } catch {
      setError("Failed to load cluster data.");
    } finally {
      setLoading(false);
    }
  }, [parentSessionId]);

  useEffect(() => {
    // Initial cluster-data fetch on mount; loadData sets loading/error state
    // before awaiting, which is the intended behaviour for a data load.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [loadData]);

  return { subRoutes, setSubRoutes, parentSession, bikers, loading, error, setError, reload: loadData };
}
