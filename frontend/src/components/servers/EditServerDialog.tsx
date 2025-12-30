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
import { Plus, Download, AlertCircle } from 'lucide-react';
import { useUpdateServer } from '@/lib/hooks/useUpdateServer';
import type { Server } from '@/lib/api/types';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';

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
      form.reset({
        name: server.name,
        modrinth_projects: server.modrinth_projects || [],
        collection_url: '',
      });
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
      const response = await fetch(
        `/api/servers/${server.id}/import-collection?collection_url=${encodeURIComponent(collectionUrl)}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error('Failed to import collection');
      }

      const result = await response.json();
      form.setValue('modrinth_projects', result.projects);
      form.setValue('collection_url', '');

      toast.success(`Added ${result.new_count} projects from collection`);
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
                    <div className="flex flex-wrap gap-2">
                      {form.watch('modrinth_projects')?.map((project) => (
                        <div
                          key={project}
                          className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md text-sm flex items-center gap-2"
                        >
                          <span>{project}</span>
                          <button
                            type="button"
                            onClick={() => handleRemoveProject(project)}
                            className="hover:text-destructive"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
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
