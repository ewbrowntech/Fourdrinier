import { useQuery } from '@tanstack/react-query';
import { getServer } from '@/lib/api/servers';

export function useServer(id: string) {
  return useQuery({
    queryKey: ['servers', id],
    queryFn: () => getServer(id),
    enabled: !!id,
    refetchInterval: (query) => {
      // Poll every 2 seconds if server is in a transitional state
      const status = query.state.data?.status;
      return status === 'pending' ? 2000 : false;
    },
  });
}
