import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { startServer } from '@/lib/api/servers';

export function useStartServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (serverId: string) => startServer(serverId),
    onSuccess: (_, serverId) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      queryClient.invalidateQueries({ queryKey: ['servers', serverId] });
      toast.success('Server started successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to start server: ${error.message}`);
    },
  });
}
