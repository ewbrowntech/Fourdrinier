import { useState } from 'react';
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

const createServerSchema = z.object({
  name: z.string().optional(),
  loader: z.string().optional(),
  game_version: z
    .string()
    .min(1, 'Game version is required')
    .regex(/^\d+\.\d+\.\d+$/, 'Version must be in format X.Y.Z (e.g., 1.20.1)'),
});

type CreateServerFormValues = z.infer<typeof createServerSchema>;

export function CreateServerDialog() {
  const [open, setOpen] = useState(false);
  const createServerMutation = useCreateServer();

  const form = useForm<CreateServerFormValues>({
    resolver: zodResolver(createServerSchema),
    defaultValues: {
      name: 'My Server',
      loader: 'paper',
      game_version: '',
    },
  });

  const onSubmit = async (data: CreateServerFormValues) => {
    createServerMutation.mutate(data, {
      onSuccess: () => {
        setOpen(false);
        form.reset();
      },
    });
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
