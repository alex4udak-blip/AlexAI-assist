import { useCallback } from 'react';
import { api, type QueryParams } from '../lib/api';
import { useApi } from './useApi';

export function usePatterns(params?: QueryParams) {
  const fetcher = useCallback(() => api.getPatterns(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function usePattern(id: string) {
  const fetcher = useCallback(() => api.getPattern(id), [id]);
  return useApi(fetcher, [id]);
}

export function useDetectPatterns(params?: QueryParams) {
  const fetcher = useCallback(() => api.detectPatterns(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useSuggestions(params?: QueryParams) {
  const fetcher = useCallback(() => api.getSuggestions(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}
