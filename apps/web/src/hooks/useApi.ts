import { useState, useEffect, useCallback, useRef } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseApiOptions {
  /** If true, refetch data when component remounts (default: true) */
  refetchOnMount?: boolean;
}

interface UseApiResult<T> extends UseApiState<T> {
  refetch: () => Promise<void>;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: UseApiOptions = {}
): UseApiResult<T> {
  const { refetchOnMount = true } = options;

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  // Track mount ID to detect remounts
  const mountIdRef = useRef(0);
  const hasFetchedRef = useRef(false);

  const fetch = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetcher();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      });
    }
  }, [fetcher]);

  // Handle refetch on mount
  useEffect(() => {
    mountIdRef.current += 1;
    const currentMountId = mountIdRef.current;

    // First mount or refetchOnMount enabled on remount
    if (!hasFetchedRef.current || refetchOnMount) {
      hasFetchedRef.current = true;
      fetch();
    }

    return () => {
      // Reset on unmount so next mount is treated as fresh
      if (currentMountId === mountIdRef.current) {
        hasFetchedRef.current = false;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle dependency changes
  useEffect(() => {
    // Skip initial mount (handled above)
    if (mountIdRef.current > 0 && hasFetchedRef.current) {
      fetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, refetch: fetch };
}

export function useMutation<T, A extends unknown[]>(
  mutator: (...args: A) => Promise<T>
): {
  mutate: (...args: A) => Promise<T>;
  loading: boolean;
  error: Error | null;
} {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (...args: A): Promise<T> => {
      setLoading(true);
      setError(null);
      try {
        const result = await mutator(...args);
        setLoading(false);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Unknown error');
        setError(error);
        setLoading(false);
        throw error;
      }
    },
    [mutator]
  );

  return { mutate, loading, error };
}
