import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { stopServer } from '@/lib/api/servers';

export function useStopServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (serverId: string) => stopServer(serverId),
    onSuccess: (_, serverId) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      queryClient.invalidateQueries({ queryKey: ['servers', serverId] });
      toast.success('Server stopped successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to stop server: ${error.message}`);
    },
  });
}
