import type { ModrinthProjectEnriched } from './types';

const MODRINTH_BASE_URL = 'https://api.modrinth.com/v3';
const MODRINTH_PROJECT_BATCH_SIZE = 100;

type ModrinthProjectResponse = {
  id: string;
  name: string;
  summary: string;
  description: string;
  icon_url?: string | null;
  game_versions?: string[];
  loaders?: string[];
};

function chunkProjectIds(projectIds: string[]): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < projectIds.length; i += MODRINTH_PROJECT_BATCH_SIZE) {
    chunks.push(projectIds.slice(i, i + MODRINTH_PROJECT_BATCH_SIZE));
  }
  return chunks;
}

function checkCompatibility(
  project: ModrinthProjectResponse,
  gameVersion: string,
  loader: string
): { compatible: boolean; warnings: string[] } {
  const warnings: string[] = [];
  let compatible = true;

  // Check game version compatibility
  const gameVersions = project.game_versions || [];
  if (gameVersions.length > 0 && !gameVersions.includes(gameVersion)) {
    compatible = false;
    const supportedVersions = gameVersions.slice(0, 5).join(', ') + (gameVersions.length > 5 ? '...' : '');
    warnings.push(`Supports versions: ${supportedVersions}`);
  }

  // Check loader compatibility
  const loaders = project.loaders || [];
  if (loaders.length > 0) {
    const normalizedLoader = loader.toLowerCase();
    const normalizedLoaders = loaders.map((l) => l.toLowerCase());
    if (!normalizedLoaders.includes(normalizedLoader)) {
      compatible = false;
      warnings.push(`Supports loaders: ${loaders.join(', ')}`);
    }
  }

  return { compatible, warnings };
}

function toProjectEnriched(
  project: ModrinthProjectResponse,
  gameVersion: string,
  loader: string
): ModrinthProjectEnriched {
  const { compatible, warnings } = checkCompatibility(project, gameVersion, loader);

  return {
    project_id: project.id,
    title: project.name,
    summary: project.summary,
    description: project.description,
    icon_url: project.icon_url ?? null,
    compatible,
    warnings,
  };
}

export async function getModrinthProjects(
  projectIds: string[],
  gameVersion: string,
  loader: string
): Promise<ModrinthProjectEnriched[]> {
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
      return data.map((project) => toProjectEnriched(project, gameVersion, loader));
    })
  );

  return responses.flat();
}
