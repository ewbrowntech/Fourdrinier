export interface Server {
  id: string;
  name: string;
  loader: string;
  game_version: string;
  status: 'running' | 'pending' | 'stopped' | 'created' | 'error';
}

export interface CreateServerInput {
  name?: string;
  loader?: string;
  game_version: string;
}

export interface UpdateServerInput {
  name: string;
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
