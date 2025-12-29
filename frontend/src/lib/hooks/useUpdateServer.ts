import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { updateServer } from '@/lib/api/servers';
import type { UpdateServerInput } from '@/lib/api/types';

export function useUpdateServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ serverId, data }: { serverId: string; data: UpdateServerInput }) =>
      updateServer(serverId, data),
    onSuccess: (_, { serverId }) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      queryClient.invalidateQueries({ queryKey: ['servers', serverId] });
      toast.success('Server updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update server: ${error.message}`);
    },
  });
}
