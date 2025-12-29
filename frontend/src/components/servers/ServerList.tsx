import { ServerCard } from './ServerCard';
import { Skeleton } from '@/components/ui/skeleton';
import { ServerOff } from 'lucide-react';
import type { Server } from '@/lib/api/types';

interface ServerListProps {
  servers: Server[];
  isLoading?: boolean;
}

export function ServerList({ servers, isLoading }: ServerListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-6 space-y-3">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (servers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 text-muted-foreground">
        <ServerOff className="h-16 w-16" />
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-1">No servers yet</h3>
          <p className="text-sm">Create your first Minecraft server to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {servers.map((server) => (
        <ServerCard key={server.id} server={server} />
      ))}
    </div>
  );
}
