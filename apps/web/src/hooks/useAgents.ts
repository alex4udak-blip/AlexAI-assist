import { useCallback } from 'react';
import { api, type Agent, type AgentCreate } from '../lib/api';
import { useApi, useMutation } from './useApi';

export function useAgents(params?: Record<string, unknown>) {
  const fetcher = useCallback(() => api.getAgents(params), [params]);
  return useApi(fetcher, [JSON.stringify(params)]);
}

export function useAgent(id: string) {
  const fetcher = useCallback(() => api.getAgent(id), [id]);
  return useApi(fetcher, [id]);
}

export function useCreateAgent() {
  return useMutation((data: AgentCreate) => api.createAgent(data));
}

export function useUpdateAgent() {
  return useMutation((id: string, data: Partial<AgentCreate>) =>
    api.updateAgent(id, data)
  );
}

export function useDeleteAgent() {
  return useMutation((id: string) => api.deleteAgent(id));
}

export function useRunAgent() {
  return useMutation((id: string, context?: Record<string, unknown>) =>
    api.runAgent(id, context)
  );
}

export function useEnableAgent() {
  return useMutation((id: string) => api.enableAgent(id));
}

export function useDisableAgent() {
  return useMutation((id: string) => api.disableAgent(id));
}

export function useAgentLogs(id: string, params?: Record<string, unknown>) {
  const fetcher = useCallback(
    () => api.getAgentLogs(id, params),
    [id, params]
  );
  return useApi(fetcher, [id, JSON.stringify(params)]);
}
