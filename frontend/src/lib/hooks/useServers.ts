import { useQuery } from '@tanstack/react-query';
import { getAllServers } from '@/lib/api/servers';

export function useServers() {
  return useQuery({
    queryKey: ['servers'],
    queryFn: getAllServers,
  });
}
