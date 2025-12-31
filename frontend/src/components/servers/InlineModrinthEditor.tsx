import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Pencil, X, Check, Plus, Download, ExternalLink } from 'lucide-react';
import type { Server, ModrinthProjectInfo } from '@/lib/api/types';
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
  onUpdate: (projects: string[]) => void;
  disabled?: boolean;
}

export function InlineModrinthEditor({ server, onUpdate, disabled }: InlineModrinthEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [projects, setProjects] = useState<string[]>(server.modrinth_projects || []);
  const [collectionUrl, setCollectionUrl] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [projectInfoMap, setProjectInfoMap] = useState<Record<string, ModrinthProjectInfo>>({});

  const isFabric = server.loader === 'fabric';

  // Fetch enriched metadata when editing starts or projects change
  useEffect(() => {
    if (!isEditing || projects.length === 0) {
      return;
    }

    const missingProjects = projects.filter((projectId) => !projectInfoMap[projectId]);
    if (missingProjects.length === 0) {
      return;
    }

    getModrinthProjects(missingProjects)
      .then((projectsData) => {
        setProjectInfoMap((prev) => {
          const next = { ...prev };
          projectsData.forEach((project) => {
            next[project.project_id] = project;
          });
          return next;
        });
      })
      .catch((err) => {
        console.error('Failed to resolve Modrinth project metadata:', err);
      });
  }, [projects, isEditing, projectInfoMap]);

  // Sync with server prop when it changes
  useEffect(() => {
    if (!isEditing) {
      setProjects(server.modrinth_projects || []);
    }
  }, [server.modrinth_projects, isEditing]);

  const handleEdit = () => {
    if (!isFabric) {
      toast.error('Modrinth projects are only available for Fabric servers');
      return;
    }
    setProjects(server.modrinth_projects || []);
    setProjectInfoMap({});
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
    const newProject = prompt('Enter Modrinth project slug/ID:');
    if (newProject && !projects.includes(newProject)) {
      setProjects([...projects, newProject]);
    }
  };

  const handleRemoveProject = (projectToRemove: string) => {
    setProjects(projects.filter((p) => p !== projectToRemove));
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
        const projectsData = await getModrinthProjects(result.projects);
        const nextMap: Record<string, ModrinthProjectInfo> = {};
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
          <div className="flex flex-wrap gap-2 flex-1">
            {projects.length === 0 ? (
              <span className="text-sm text-muted-foreground">No mods installed</span>
            ) : (
              projects.map((projectId) => {
                const projectInfo = projectInfoMap[projectId];
                const displayName = projectInfo?.title || projectId;
                const modrinthUrl = `https://modrinth.com/mod/${projectId}`;

                return (
                  <Tooltip key={projectId}>
                    <TooltipTrigger asChild>
                      <div className="bg-secondary text-secondary-foreground px-2 py-1 rounded-md text-sm flex items-center gap-1.5">
                        {projectInfo?.icon_url && (
                          <img
                            src={projectInfo.icon_url}
                            alt={displayName}
                            className="h-4 w-4 rounded"
                          />
                        )}
                        <span>{displayName}</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
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
                    </TooltipContent>
                  </Tooltip>
                );
              })
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
      {/* Display current projects as editable tags */}
      <TooltipProvider>
        <div className="flex flex-wrap gap-2">
          {projects.length === 0 ? (
            <span className="text-sm text-muted-foreground">No projects added yet</span>
          ) : (
            projects.map((projectId) => {
              const projectInfo = projectInfoMap[projectId];
              const displayName = projectInfo?.title || projectId;
              const modrinthUrl = `https://modrinth.com/mod/${projectId}`;

              return (
                <Tooltip key={projectId}>
                  <TooltipTrigger asChild>
                    <div className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md text-sm flex items-center gap-2">
                      {projectInfo?.icon_url && (
                        <img
                          src={projectInfo.icon_url}
                          alt={displayName}
                          className="h-4 w-4 rounded"
                        />
                      )}
                      <span>{displayName}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveProject(projectId)}
                        className="hover:text-destructive"
                      >
                        ×
                      </button>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
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
                  </TooltipContent>
                </Tooltip>
              );
            })
          )}
        </div>
      </TooltipProvider>

      {/* Add project button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAddProject}
      >
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
          Paste a Modrinth collection URL to import all projects
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
