import { useCallback } from 'react';
import { api } from '../lib/api';
import { useApi } from './useApi';

export function usePatterns(params?: Record<string, unknown>) {
  const fetcher = useCallback(() => api.getPatterns(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function usePattern(id: string) {
  const fetcher = useCallback(() => api.getPattern(id), [id]);
  return useApi(fetcher, [id]);
}

export function useDetectPatterns(params?: Record<string, unknown>) {
  const fetcher = useCallback(() => api.detectPatterns(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useSuggestions(params?: Record<string, unknown>) {
  const fetcher = useCallback(() => api.getSuggestions(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}
