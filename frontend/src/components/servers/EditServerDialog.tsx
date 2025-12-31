import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Plus, Download, AlertCircle, ExternalLink } from 'lucide-react';
import { useUpdateServer } from '@/lib/hooks/useUpdateServer';
import type { Server, ModrinthProjectInfo } from '@/lib/api/types';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { importCollection } from '@/lib/api/servers';
import { getModrinthProjects } from '@/lib/api/modrinth';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const editServerSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  modrinth_projects: z.array(z.string()).optional(),
  collection_url: z.string().optional(),
});

type EditServerFormValues = z.infer<typeof editServerSchema>;

interface EditServerDialogProps {
  server: Server | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditServerDialog({ server, open, onOpenChange }: EditServerDialogProps) {
  const [isImporting, setIsImporting] = useState(false);
  const [projectInfoMap, setProjectInfoMap] = useState<Record<string, ModrinthProjectInfo>>({});
  const updateServerMutation = useUpdateServer();

  const form = useForm<EditServerFormValues>({
    resolver: zodResolver(editServerSchema),
    defaultValues: {
      name: '',
      modrinth_projects: [],
      collection_url: '',
    },
  });

  // Load server data when dialog opens
  useEffect(() => {
    if (server && open) {
      setProjectInfoMap({});
      form.reset({
        name: server.name,
        modrinth_projects: server.modrinth_projects || [],
        collection_url: '',
      });

      // Fetch enriched metadata for display
      if (server.modrinth_projects && server.modrinth_projects.length > 0) {
        getModrinthProjects(server.modrinth_projects)
          .then((projects) => {
            const nextMap: Record<string, ModrinthProjectInfo> = {};
            projects.forEach((project) => {
              nextMap[project.project_id] = project;
            });
            setProjectInfoMap(nextMap);
          })
          .catch((err) => {
            console.error('Failed to fetch enriched project metadata:', err);
            setProjectInfoMap({});
          });
      }
    }
  }, [server, open, form]);

  const onSubmit = async (data: EditServerFormValues) => {
    if (!server) return;

    const { collection_url, ...submitData } = data;
    updateServerMutation.mutate(
      { serverId: server.id, data: submitData },
      {
        onSuccess: () => {
          toast.success('Mods updated. Restart server to apply changes.');
          onOpenChange(false);
        },
        onError: () => {
          toast.error('Failed to update server');
        },
      }
    );
  };

  const handleImportCollection = async () => {
    if (!server) return;
    const collectionUrl = form.getValues('collection_url');
    if (!collectionUrl) {
      toast.error('Please enter a collection URL');
      return;
    }

    setIsImporting(true);
    try {
      const result = await importCollection(server.id, collectionUrl);
      form.setValue('modrinth_projects', result.projects);
      form.setValue('collection_url', '');

      // Refresh enriched metadata after import
      if (result.projects.length > 0) {
        const projects = await getModrinthProjects(result.projects);
        const nextMap: Record<string, ModrinthProjectInfo> = {};
        projects.forEach((project) => {
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

  const handleAddProject = () => {
    const currentProjects = form.getValues('modrinth_projects') || [];
    const newProject = prompt('Enter Modrinth project slug/ID:');
    if (newProject && !currentProjects.includes(newProject)) {
      form.setValue('modrinth_projects', [...currentProjects, newProject]);
    }
  };

  const handleRemoveProject = (projectToRemove: string) => {
    const currentProjects = form.getValues('modrinth_projects') || [];
    form.setValue(
      'modrinth_projects',
      currentProjects.filter((p) => p !== projectToRemove)
    );
  };

  const isFabric = server?.loader === 'fabric';
  const modrinthProjects = form.watch('modrinth_projects') || [];

  useEffect(() => {
    if (!open || modrinthProjects.length === 0) {
      return;
    }

    const missingProjects = modrinthProjects.filter((projectId) => !projectInfoMap[projectId]);
    if (missingProjects.length === 0) {
      return;
    }

    getModrinthProjects(missingProjects)
      .then((projects) => {
        setProjectInfoMap((prev) => {
          const next = { ...prev };
          projects.forEach((project) => {
            next[project.project_id] = project;
          });
          return next;
        });
      })
      .catch((err) => {
        console.error('Failed to resolve Modrinth project metadata:', err);
      });
  }, [modrinthProjects, open, projectInfoMap]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Server</DialogTitle>
          <DialogDescription>
            Update server settings. Changes will take effect on next server restart.
          </DialogDescription>
        </DialogHeader>

        {/* Restart warning */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Changes will take effect on next server restart
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Server Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Modrinth Projects - only editable for Fabric servers */}
            <div className="space-y-3">
              <FormLabel>Modrinth Projects</FormLabel>
              {!isFabric && (
                <FormDescription>
                  Modrinth projects are only available for Fabric servers
                </FormDescription>
              )}

              {isFabric && (
                <>
                  <FormDescription>
                    Manage Modrinth mod projects for automatic installation
                  </FormDescription>

                  {/* Display current projects as tags */}
                  {(form.watch('modrinth_projects')?.length ?? 0) > 0 ? (
                    <TooltipProvider>
                      <div className="flex flex-wrap gap-2">
                        {form.watch('modrinth_projects')?.map((projectId) => {
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
                                  Modrinth
                                </a>
                              </TooltipContent>
                            </Tooltip>
                          );
                        })}
                      </div>
                    </TooltipProvider>
                  ) : (
                    <div className="text-sm text-muted-foreground">No projects added yet</div>
                  )}

                  {/* Add project button */}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddProject}
                    disabled={!isFabric}
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    Add Project
                  </Button>

                  {/* Collection import */}
                  <div className="space-y-2 pt-2">
                    <FormLabel className="text-sm">Import from Collection</FormLabel>
                    <div className="flex gap-2">
                      <Input
                        placeholder="https://modrinth.com/collection/..."
                        value={form.watch('collection_url') || ''}
                        onChange={(e) => form.setValue('collection_url', e.target.value)}
                        disabled={!isFabric}
                      />
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={handleImportCollection}
                        disabled={!isFabric || isImporting}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        {isImporting ? 'Importing...' : 'Import'}
                      </Button>
                    </div>
                    <FormDescription className="text-xs">
                      Paste a Modrinth collection URL to import all projects
                    </FormDescription>
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateServerMutation.isPending}>
                {updateServerMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
