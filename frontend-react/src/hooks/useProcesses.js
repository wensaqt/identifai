import { useCallback, useEffect, useState } from "react";
import { get, del } from "../api/client";

export function useProcesses() {
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await get("/processes");
      setProcesses(data);
    } catch {
      setProcesses([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const cancel = useCallback(async (id) => {
    await del(`/processes/${id}`);
    await refresh();
  }, [refresh]);

  useEffect(() => { refresh(); }, [refresh]);

  return { processes, loading, refresh, cancel };
}
