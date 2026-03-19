import { useCallback, useEffect, useState } from "react";
import { get } from "../api/client";

export function useProcess(processId) {
  const [process, setProcess] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await get(`/processes/${processId}`);
      setProcess(data);
    } catch {
      setProcess(null);
    } finally {
      setLoading(false);
    }
  }, [processId]);

  useEffect(() => { refresh(); }, [refresh]);

  return { process, loading, refresh, setProcess };
}
