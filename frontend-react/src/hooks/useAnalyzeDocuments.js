import { useCallback, useState } from "react";
import { post, ApiError } from "../api/client";

/**
 * Hook for calling POST /analyze.
 *
 * @returns {{ analyze, data, error, loading, reset }}
 *   - analyze(filesMap): filesMap = { [docType]: File }
 *   - data: Process payload on success
 *   - error: { type, missing?, message } on failure
 */
export function useAnalyzeDocuments() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = useCallback(async (filesMap) => {
    setLoading(true);
    setError(null);
    setData(null);

    const formData = new FormData();
    const docTypes = [];

    for (const [docType, file] of Object.entries(filesMap)) {
      if (!file) continue;
      formData.append("files", file);
      docTypes.push(docType);
    }

    formData.append("doc_types", JSON.stringify(docTypes));

    try {
      const result = await post("/analyze", { formData });
      setData(result);
      return result;
    } catch (err) {
      if (err instanceof ApiError && err.detail?.error === "missing_documents") {
        setError({ type: "missing_documents", missing: err.detail.missing, message: err.detail.message });
      } else {
        setError({ type: "server_error", message: err.message });
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { analyze, data, error, loading, reset };
}
