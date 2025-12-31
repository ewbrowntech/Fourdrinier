export type ModrinthProjectType = 'mod' | 'datapack' | 'shader' | 'resourcepack' | 'plugin';

export interface ModrinthProject {
  id: string;
  type: ModrinthProjectType;
}

export interface Server {
  id: string;
  name: string;
  loader: string;
  game_version: string;
  modrinth_projects?: ModrinthProject[] | null;
  status: 'running' | 'pending' | 'stopped' | 'created' | 'error';

  // Resource allocation
  cpu_request?: string | null;
  cpu_limit?: string | null;
  memory_request?: string | null;
  memory_limit?: string | null;
  pvc_size?: string | null;
}

export interface CreateServerInput {
  name?: string;
  loader?: string;
  game_version: string;
  modrinth_projects?: ModrinthProject[] | null;

  // Resource allocation
  cpu_request?: string | null;
  cpu_limit?: string | null;
  memory_request?: string | null;
  memory_limit?: string | null;
  pvc_size?: string | null;
}

export interface UpdateServerInput {
  name: string;
  modrinth_projects?: ModrinthProject[] | null;

  // Resource allocation (can only be updated when server is stopped)
  // Note: pvc_size NOT included - cannot be changed after creation
  cpu_request?: string | null;
  cpu_limit?: string | null;
  memory_request?: string | null;
  memory_limit?: string | null;
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

export interface ModrinthProjectEnriched {
  project_id: string;
  title: string;
  summary: string;
  description: string;
  icon_url?: string | null;
  compatible: boolean;
  warnings: string[];
  project_type: ModrinthProjectType;
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
  projects: ModrinthProject[];
  new_count: number;
  total_count: number;
  warnings: string[];
  incompatible_projects: IncompatibleProject[];
}
