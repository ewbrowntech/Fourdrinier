import { useServers } from '@/lib/hooks/useServers';
import { ServerList } from '@/components/servers/ServerList';
import { CreateServerDialog } from '@/components/servers/CreateServerDialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export function ServersPage() {
  const { data: servers, isLoading, isError, error } = useServers();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Minecraft Servers</h1>
          <p className="text-muted-foreground mt-1">
            Manage your Minecraft server deployments
          </p>
        </div>
        <CreateServerDialog />
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load servers: {error instanceof Error ? error.message : 'Unknown error'}
          </AlertDescription>
        </Alert>
      )}

      <ServerList servers={servers || []} isLoading={isLoading} />
    </div>
  );
}
