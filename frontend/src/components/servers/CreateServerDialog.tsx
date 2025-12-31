import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { useCreateServer } from '@/lib/hooks/useCreateServer';
import { getModrinthProjects } from '@/lib/api/modrinth';
import type { ModrinthProjectInfo } from '@/lib/api/types';

const createServerSchema = z.object({
  name: z.string().optional(),
  loader: z.string().optional(),
  game_version: z
    .string()
    .min(1, 'Game version is required')
    .regex(/^\d+\.\d+\.\d+$/, 'Version must be in format X.Y.Z (e.g., 1.20.1)'),
  modrinth_projects: z.array(z.string()).optional(),
  collection_url: z.string().optional(), // Temporary field for collection import
});

type CreateServerFormValues = z.infer<typeof createServerSchema>;

export function CreateServerDialog() {
  const [open, setOpen] = useState(false);
  const [projectInfoMap, setProjectInfoMap] = useState<Record<string, ModrinthProjectInfo>>({});
  const createServerMutation = useCreateServer();

  const form = useForm<CreateServerFormValues>({
    resolver: zodResolver(createServerSchema),
    defaultValues: {
      name: 'My Server',
      loader: 'paper',
      game_version: '',
      modrinth_projects: [],
      collection_url: '',
    },
  });

  const onSubmit = async (data: CreateServerFormValues) => {
    // Remove collection_url from submission (it's only for UI)
    const { collection_url, ...submitData } = data;
    createServerMutation.mutate(submitData, {
      onSuccess: () => {
        setOpen(false);
        form.reset();
      },
    });
  };

  const handleImportCollection = async () => {
    const collectionUrl = form.getValues('collection_url');
    if (!collectionUrl) return;

    try {
      // This is a simplified version - in a real implementation, you'd call the import API
      // For now, we'll just show a message that this needs backend integration
      alert('Collection import will be implemented with the EditServerDialog component');
    } catch (error) {
      console.error('Failed to import collection:', error);
    }
  };

  const modrinthProjects = form.watch('modrinth_projects') || [];

  useEffect(() => {
    if (modrinthProjects.length === 0) {
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
  }, [modrinthProjects, projectInfoMap]);

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

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Server
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create Minecraft Server</DialogTitle>
          <DialogDescription>
            Configure your new Minecraft server. Click create when you're done.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Server Name</FormLabel>
                  <FormControl>
                    <Input placeholder="My Server" {...field} />
                  </FormControl>
                  <FormDescription>A friendly name for your server</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="loader"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Server Loader</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a loader" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="paper">Paper</SelectItem>
                      <SelectItem value="vanilla">Vanilla</SelectItem>
                      <SelectItem value="forge">Forge</SelectItem>
                      <SelectItem value="fabric">Fabric</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>The server software to use</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="game_version"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Game Version</FormLabel>
                  <FormControl>
                    <Input placeholder="1.20.1" {...field} />
                  </FormControl>
                  <FormDescription>Format: X.Y.Z (e.g., 1.20.1)</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Modrinth Projects - only show for Fabric */}
            {form.watch('loader') === 'fabric' && (
              <div className="space-y-3">
                <FormLabel>Modrinth Projects (Optional)</FormLabel>
                <FormDescription>
                  Add Modrinth mod projects for automatic installation
                </FormDescription>

                {/* Display current projects as tags */}
                {form.watch('modrinth_projects')?.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {form.watch('modrinth_projects')?.map((projectId) => {
                      const projectInfo = projectInfoMap[projectId];
                      const displayName = projectInfo?.title || projectId;

                      return (
                        <div
                          key={projectId}
                          className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md text-sm flex items-center gap-2"
                        >
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
                      );
                    })}
                  </div>
                )}

                {/* Add project button */}
                <Button type="button" variant="outline" size="sm" onClick={handleAddProject}>
                  <Plus className="h-3 w-3 mr-1" />
                  Add Project
                </Button>

                {/* Collection import (simplified for now) */}
                <div className="text-xs text-muted-foreground pt-2">
                  Tip: Collection import available after server creation via Edit dialog
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createServerMutation.isPending}>
                {createServerMutation.isPending ? 'Creating...' : 'Create Server'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
