import { useCallback } from 'react';
import { api, type QueryParams } from '../lib/api';
import { useApi } from './useApi';

export function useAnalyticsSummary(params?: QueryParams) {
  const fetcher = useCallback(() => api.getSummary(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useCategories(params?: QueryParams) {
  const fetcher = useCallback(() => api.getCategories(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useAppUsage(params?: QueryParams) {
  const fetcher = useCallback(() => api.getAppUsage(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useProductivity(params?: QueryParams) {
  const fetcher = useCallback(() => api.getProductivity(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useTrends(params?: QueryParams) {
  const fetcher = useCallback(() => api.getTrends(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useTimeline(hours = 24) {
  const fetcher = useCallback(() => api.getTimeline(hours), [hours]);
  return useApi(fetcher, [hours]);
}

export function useAIUsage(days = 7) {
  const fetcher = useCallback(() => api.getAIUsage(days), [days]);
  return useApi(fetcher, [days]);
}
