import { useQuery } from '@tanstack/react-query';
import { getServer } from '@/lib/api/servers';

export function useServer(id: string) {
  return useQuery({
    queryKey: ['servers', id],
    queryFn: () => getServer(id),
    enabled: !!id,
  });
}
