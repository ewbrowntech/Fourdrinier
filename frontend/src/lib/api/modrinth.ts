import type { ModrinthProjectInfo } from './types';

const MODRINTH_BASE_URL = 'https://api.modrinth.com/v3';
const MODRINTH_PROJECT_BATCH_SIZE = 100;

type ModrinthProjectResponse = {
  id: string;
  name: string;
  description: string;
  icon_url?: string | null;
};

function chunkProjectIds(projectIds: string[]): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < projectIds.length; i += MODRINTH_PROJECT_BATCH_SIZE) {
    chunks.push(projectIds.slice(i, i + MODRINTH_PROJECT_BATCH_SIZE));
  }
  return chunks;
}

function toProjectInfo(project: ModrinthProjectResponse): ModrinthProjectInfo {
  return {
    project_id: project.id,
    title: project.name,
    description: project.description,
    icon_url: project.icon_url ?? null,
  };
}

export async function getModrinthProjects(projectIds: string[]): Promise<ModrinthProjectInfo[]> {
  const uniqueIds = Array.from(new Set(projectIds.filter(Boolean)));
  if (uniqueIds.length === 0) {
    return [];
  }

  const batches = chunkProjectIds(uniqueIds);
  const responses = await Promise.all(
    batches.map(async (batch) => {
      const idsParam = encodeURIComponent(JSON.stringify(batch));
      const response = await fetch(`${MODRINTH_BASE_URL}/projects?ids=${idsParam}`);
      if (!response.ok) {
        throw new Error(`Modrinth lookup failed: ${response.status}`);
      }
      const data = (await response.json()) as ModrinthProjectResponse[];
      return data.map(toProjectInfo);
    })
  );

  return responses.flat();
}
