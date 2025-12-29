import { apiClient } from './client';
import type {
  Server,
  CreateServerInput,
  UpdateServerInput,
  StartServerResponse,
  StopServerResponse,
  DeleteServerResponse,
} from './types';

export async function getAllServers(): Promise<Server[]> {
  const response = await apiClient.get<Server[]>('/servers/');
  return response.data;
}

export async function getServer(id: string): Promise<Server> {
  const response = await apiClient.get<Server>(`/servers/${id}`);
  return response.data;
}

export async function createServer(data: CreateServerInput): Promise<Server> {
  const response = await apiClient.post<Server>('/servers/', data);
  return response.data;
}

export async function updateServer(id: string, data: UpdateServerInput): Promise<Server> {
  const response = await apiClient.put<Server>(`/servers/${id}`, data);
  return response.data;
}

export async function startServer(id: string): Promise<StartServerResponse> {
  const response = await apiClient.post<StartServerResponse>(`/servers/${id}/start`);
  return response.data;
}

export async function stopServer(id: string): Promise<StopServerResponse> {
  const response = await apiClient.put<StopServerResponse>(`/servers/${id}/stop`);
  return response.data;
}

export async function deleteServer(id: string): Promise<DeleteServerResponse> {
  const response = await apiClient.delete<DeleteServerResponse>(`/servers/${id}`);
  return response.data;
}
