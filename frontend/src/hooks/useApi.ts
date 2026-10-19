import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../services/api";
export function useApi<T>(path: string) {
  const [response, setResponse] = useState<{ path: string; data: T }>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api
      .get<T>(path, { signal: controller.signal })
      .then((r) => {
        if (!controller.signal.aborted) setResponse({ path, data: r.data });
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(errorMessage(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, version]);
  return {
    data: response?.path === path ? response.data : undefined,
    error,
    loading,
    reload,
  };
}
