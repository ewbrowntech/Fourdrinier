import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Pencil, X, Check, Plus, Download, ExternalLink } from 'lucide-react';
import type { Server, ModrinthProjectEnriched, ModrinthProject, ModrinthProjectType } from '@/lib/api/types';
import { toast } from 'sonner';
import { importCollection } from '@/lib/api/servers';
import { getModrinthProjects } from '@/lib/api/modrinth';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface InlineModrinthEditorProps {
  server: Server;
  onUpdate: (projects: ModrinthProject[]) => void;
  disabled?: boolean;
}

const TYPE_LABELS: Record<ModrinthProjectType, string> = {
  mod: 'Mods',
  datapack: 'Datapacks',
  shader: 'Shaders',
  resourcepack: 'Resource Packs',
  plugin: 'Plugins',
};

export function InlineModrinthEditor({ server, onUpdate, disabled }: InlineModrinthEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [projects, setProjects] = useState<ModrinthProject[]>(server.modrinth_projects || []);
  const [collectionUrl, setCollectionUrl] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [projectInfoMap, setProjectInfoMap] = useState<Record<string, ModrinthProjectEnriched>>({});

  const isFabric = server.loader === 'fabric';

  // Sync with server prop when it changes
  useEffect(() => {
    if (!isEditing) {
      setProjects(server.modrinth_projects || []);
    }
  }, [server.modrinth_projects, isEditing]);

  // Fetch enriched metadata with compatibility info whenever server's mods change
  useEffect(() => {
    if (!server.modrinth_projects || server.modrinth_projects.length === 0 || !isFabric) {
      setProjectInfoMap({});
      return;
    }

    const projectIds = server.modrinth_projects.map((p) => p.id);
    getModrinthProjects(projectIds, server.game_version, server.loader)
      .then((projectsData) => {
        const nextMap: Record<string, ModrinthProjectEnriched> = {};
        projectsData.forEach((project) => {
          nextMap[project.project_id] = project;
        });
        setProjectInfoMap(nextMap);
      })
      .catch((err) => {
        console.error('Failed to resolve Modrinth project metadata:', err);
        setProjectInfoMap({});
      });
  }, [server.modrinth_projects, server.game_version, server.loader, isFabric]);

  const handleEdit = () => {
    if (!isFabric) {
      toast.error('Modrinth projects are only available for Fabric servers');
      return;
    }
    setProjects(server.modrinth_projects || []);
    setIsEditing(true);
  };

  const handleCancel = () => {
    setProjects(server.modrinth_projects || []);
    setCollectionUrl('');
    setIsEditing(false);
  };

  const handleSave = () => {
    onUpdate(projects);
    setIsEditing(false);
  };

  const handleAddProject = () => {
    const newProjectId = prompt('Enter Modrinth project slug/ID:');
    if (!newProjectId) return;

    // Check if already exists
    if (projects.some((p) => p.id === newProjectId)) {
      toast.error('Project already added');
      return;
    }

    // Prompt for type or auto-detect
    const typeInput = prompt(
      'Enter project type (mod/datapack/shader/resourcepack/plugin) or leave blank to auto-detect:'
    );

    if (typeInput && !['mod', 'datapack', 'shader', 'resourcepack', 'plugin', ''].includes(typeInput)) {
      toast.error('Invalid project type');
      return;
    }

    if (!typeInput) {
      // Auto-detect from Modrinth API
      getModrinthProjects([newProjectId], server.game_version, server.loader)
        .then((projectsData) => {
          if (projectsData.length > 0) {
            const projectType = projectsData[0].project_type;
            setProjects([...projects, { id: newProjectId, type: projectType }]);
            toast.success(`Added ${newProjectId} as ${projectType}`);
          } else {
            toast.error('Project not found on Modrinth');
          }
        })
        .catch(() => {
          toast.error('Failed to fetch project metadata');
        });
    } else {
      // Manual type specification
      setProjects([...projects, { id: newProjectId, type: typeInput as ModrinthProjectType }]);
      toast.success(`Added ${newProjectId} as ${typeInput}`);
    }
  };

  const handleRemoveProject = (projectIdToRemove: string) => {
    setProjects(projects.filter((p) => p.id !== projectIdToRemove));
  };

  const handleImportCollection = async () => {
    if (!collectionUrl) {
      toast.error('Please enter a collection URL');
      return;
    }

    setIsImporting(true);
    try {
      const result = await importCollection(server.id, collectionUrl);
      setProjects(result.projects);
      setCollectionUrl('');

      // Refresh enriched metadata after import
      if (result.projects.length > 0) {
        const projectIds = result.projects.map((p) => p.id);
        const projectsData = await getModrinthProjects(projectIds, server.game_version, server.loader);
        const nextMap: Record<string, ModrinthProjectEnriched> = {};
        projectsData.forEach((project) => {
          nextMap[project.project_id] = project;
        });
        setProjectInfoMap(nextMap);
      }

      // Show warning if incompatible projects detected
      if (result.warnings.length > 0) {
        toast.warning(`Added ${result.new_count} projects. ${result.incompatible_projects.length} may be incompatible.`);
      } else {
        toast.success(`Added ${result.new_count} projects from collection`);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to import collection');
    } finally {
      setIsImporting(false);
    }
  };

  // Group projects by type
  const groupedProjects = projects.reduce((acc, project) => {
    const type = project.type || 'mod';
    if (!acc[type]) acc[type] = [];
    acc[type].push(project);
    return acc;
  }, {} as Record<string, ModrinthProject[]>);

  // Render a single project pill
  const renderProjectPill = (project: ModrinthProject, showRemove = false) => {
    const projectInfo = projectInfoMap[project.id];
    const displayName = projectInfo?.title || project.id;
    const modrinthUrl = `https://modrinth.com/${project.type}/${project.id}`;
    const isIncompatible = projectInfo && !projectInfo.compatible;

    return (
      <Tooltip key={project.id}>
        <TooltipTrigger asChild>
          <div
            className={`px-${showRemove ? '3' : '2'} py-1 rounded-md text-sm flex items-center gap-${showRemove ? '2' : '1.5'} ${
              isIncompatible
                ? 'bg-yellow-500/20 text-yellow-900 dark:text-yellow-100 border border-yellow-500/50'
                : 'bg-secondary text-secondary-foreground'
            }`}
          >
            {projectInfo?.icon_url && (
              <img src={projectInfo.icon_url} alt={displayName} className="h-4 w-4 rounded" />
            )}
            <span>{displayName}</span>
            {showRemove && (
              <button
                type="button"
                onClick={() => handleRemoveProject(project.id)}
                className="hover:text-destructive"
              >
                ×
              </button>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <div className="space-y-2">
            {projectInfo?.summary && (
              <p className="text-xs text-muted-foreground">{projectInfo.summary}</p>
            )}
            {isIncompatible && projectInfo.warnings.length > 0 && (
              <div className="text-xs text-yellow-600 dark:text-yellow-400">
                <div className="font-semibold mb-1">Incompatible:</div>
                {projectInfo.warnings.map((warning, idx) => (
                  <div key={idx}>{warning}</div>
                ))}
              </div>
            )}
            <a
              href={modrinthUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="h-3 w-3" />
              View on Modrinth
            </a>
          </div>
        </TooltipContent>
      </Tooltip>
    );
  };

  if (!isFabric) {
    return (
      <div className="text-sm text-muted-foreground">
        Not available for {server.loader} servers
      </div>
    );
  }

  if (!isEditing) {
    return (
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <div className="flex-1 space-y-3">
            {projects.length === 0 ? (
              <span className="text-sm text-muted-foreground">No projects installed</span>
            ) : (
              Object.entries(groupedProjects).map(([type, typeProjects]) => (
                <div key={type}>
                  <h4 className="text-xs font-medium text-muted-foreground mb-1.5">
                    {TYPE_LABELS[type as ModrinthProjectType]}
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {typeProjects.map((project) => renderProjectPill(project, false))}
                  </div>
                </div>
              ))
            )}
          </div>
        </TooltipProvider>
        {!disabled && (
          <Button variant="ghost" size="sm" onClick={handleEdit}>
            <Pencil className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3 border rounded-lg p-3">
      {/* Display current projects as editable tags, grouped by type */}
      <TooltipProvider>
        <div className="space-y-3">
          {projects.length === 0 ? (
            <span className="text-sm text-muted-foreground">No projects added yet</span>
          ) : (
            Object.entries(groupedProjects).map(([type, typeProjects]) => (
              <div key={type}>
                <h4 className="text-sm font-medium mb-2">
                  {TYPE_LABELS[type as ModrinthProjectType]}
                </h4>
                <div className="flex flex-wrap gap-2">
                  {typeProjects.map((project) => renderProjectPill(project, true))}
                </div>
              </div>
            ))
          )}
        </div>
      </TooltipProvider>

      {/* Add project button */}
      <Button type="button" variant="outline" size="sm" onClick={handleAddProject}>
        <Plus className="h-3 w-3 mr-1" />
        Add Project
      </Button>

      {/* Collection import */}
      <div className="space-y-2">
        <div className="text-sm font-medium">Import from Collection</div>
        <div className="flex gap-2">
          <Input
            placeholder="https://modrinth.com/collection/..."
            value={collectionUrl}
            onChange={(e) => setCollectionUrl(e.target.value)}
            className="flex-1"
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleImportCollection}
            disabled={isImporting}
          >
            <Download className="h-3 w-3 mr-1" />
            {isImporting ? 'Importing...' : 'Import'}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Paste a Modrinth collection URL to import all projects (types auto-detected)
        </p>
      </div>

      {/* Save/Cancel buttons */}
      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={handleSave}>
          <Check className="h-3 w-3 mr-1" />
          Save
        </Button>
        <Button size="sm" variant="outline" onClick={handleCancel}>
          <X className="h-3 w-3 mr-1" />
          Cancel
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        Changes will take effect on next server restart
      </p>
    </div>
  );
}
