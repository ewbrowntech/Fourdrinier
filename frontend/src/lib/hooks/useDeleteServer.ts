import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { deleteServer } from '@/lib/api/servers';

export function useDeleteServer() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (serverId: string) => deleteServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      toast.success('Server deleted successfully');
      navigate('/');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete server: ${error.message}`);
    },
  });
}
