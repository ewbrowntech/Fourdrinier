import { apiClient } from './client';
import type {
  Server,
  CreateServerInput,
  UpdateServerInput,
  StartServerResponse,
  StopServerResponse,
  DeleteServerResponse,
  ImportCollectionResponse,
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

export function getServerLogsUrl(id: string): string {
  const baseUrl = apiClient.defaults.baseURL || '';
  return `${baseUrl}/servers/${id}/logs`;
}

export async function importCollection(id: string, collectionUrl: string): Promise<ImportCollectionResponse> {
  const response = await apiClient.post<ImportCollectionResponse>(
    `/servers/${id}/import-collection`,
    null,
    { params: { collection_url: collectionUrl } }
  );
  return response.data;
}

export async function exportServerAsMrpack(id: string): Promise<void> {
  const response = await apiClient.get(`/servers/${id}/export-mrpack`, {
    responseType: 'blob',
  });

  // Extract filename from Content-Disposition header or use default
  const contentDisposition = response.headers['content-disposition'];
  let filename = `server-${id}.mrpack`;

  if (contentDisposition) {
    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
    if (matches != null && matches[1]) {
      filename = matches[1].replace(/['"]/g, '');
    }
  }

  // Create blob and trigger download
  const blob = new Blob([response.data], { type: 'application/x-modrinth-modpack+zip' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
