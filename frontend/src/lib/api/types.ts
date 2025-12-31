export interface Server {
  id: string;
  name: string;
  loader: string;
  game_version: string;
  modrinth_projects?: string[] | null;
  status: 'running' | 'pending' | 'stopped' | 'created' | 'error';
}

export interface CreateServerInput {
  name?: string;
  loader?: string;
  game_version: string;
  modrinth_projects?: string[] | null;
}

export interface UpdateServerInput {
  name: string;
  modrinth_projects?: string[] | null;
}

export interface StartServerResponse {
  pod: {
    name: string;
    namespace: string;
  };
  pvc: {
    name: string;
    namespace: string;
  };
  service: {
    name: string;
    namespace: string;
  };
}

export interface StopServerResponse {
  message: string;
}

export interface DeleteServerResponse {
  message: string;
}

export interface ModrinthProjectInfo {
  project_id: string;
  title: string;
  description: string;
  icon_url?: string | null;
}

export interface IncompatibleProject {
  project_id: string;
  title: string;
  reason: string;
  supported_versions: string[];
  supported_loaders: string[];
}

export interface ImportCollectionResponse {
  message: string;
  projects: string[];
  new_count: number;
  total_count: number;
  warnings: string[];
  incompatible_projects: IncompatibleProject[];
}
