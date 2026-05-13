/**
 * Generic polling hook.
 *
 * Calls `fetcher` immediately, then on a fixed interval. Returns the latest
 * data, the error from the most recent attempt, and a manual `refetch`.
 * Pauses while the screen is unfocused to save battery.
 */
import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';

interface PollState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  refetch: () => Promise<void>;
}

export function usePoll<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  options: { runWhileBlurred?: boolean } = {},
): PollState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const focusedRef = useRef(true);
  const mountedRef = useRef(true);

  const run = useCallback(async () => {
    try {
      const next = await fetcher();
      if (mountedRef.current) {
        setData(next);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [fetcher]);

  useFocusEffect(
    useCallback(() => {
      focusedRef.current = true;
      void run();
      const id = setInterval(() => {
        if (focusedRef.current || options.runWhileBlurred) {
          void run();
        }
      }, intervalMs);
      return () => {
        focusedRef.current = false;
        clearInterval(id);
      };
    }, [intervalMs, options.runWhileBlurred, run]),
  );

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return { data, error, loading, refetch: run };
}
