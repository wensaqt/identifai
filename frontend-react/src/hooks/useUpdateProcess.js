import { useCallback, useState } from "react";
import { ApiError } from "../api/client";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export function useUpdateProcess() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const update = useCallback(async (processId, filesMap, processType) => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    const docTypes = [];

    for (const [docType, file] of Object.entries(filesMap)) {
      if (!file) continue;
      formData.append("files", file);
      docTypes.push(docType);
    }

    formData.append("doc_types", JSON.stringify(docTypes));
    if (processType) {
      formData.append("process_type", processType);
    }

    try {
      const res = await fetch(`${BASE_URL}/processes/${processId}`, {
        method: "PUT",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail ?? data;
        if (detail?.error === "missing_documents") {
          setError({ type: "missing_documents", missing: detail.missing, message: detail.message });
        } else {
          setError({ type: "server_error", message: detail?.message || `HTTP ${res.status}` });
        }
        return null;
      }
      return data;
    } catch (err) {
      setError({ type: "server_error", message: err.message });
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const resetError = useCallback(() => setError(null), []);

  return { update, loading, error, resetError };
}
