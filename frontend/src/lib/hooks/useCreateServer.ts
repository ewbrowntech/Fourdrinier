import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createServer } from '@/lib/api/servers';
import type { CreateServerInput } from '@/lib/api/types';

export function useCreateServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateServerInput) => createServer(data),
    onSuccess: (server) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      toast.success(`Server "${server.name}" created successfully`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to create server: ${error.message}`);
    },
  });
}
