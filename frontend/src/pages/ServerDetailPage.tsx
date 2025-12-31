import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useServer } from '@/lib/hooks/useServer';
import { useStartServer } from '@/lib/hooks/useStartServer';
import { useStopServer } from '@/lib/hooks/useStopServer';
import { useDeleteServer } from '@/lib/hooks/useDeleteServer';
import { useUpdateServer } from '@/lib/hooks/useUpdateServer';
import { exportServerAsMrpack } from '@/lib/api/servers';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Play, Square, Trash2, AlertCircle, Pencil, Check, X, Download } from 'lucide-react';
import { ServerLogs } from '@/components/servers/ServerLogs';
import { InlineModrinthEditor } from '@/components/servers/InlineModrinthEditor';
import { InlineResourceEditor } from '@/components/servers/InlineResourceEditor';
import type { ModrinthProject } from '@/lib/api/types';

function countProjectsByType(projects: ModrinthProject[] | null | undefined) {
  const counts = { mods: 0, datapacks: 0, shaders: 0, resourcepacks: 0, plugins: 0 };
  if (!projects) return counts;

  for (const project of projects) {
    const type = project.type || 'mod';
    if (type === 'datapack') {
      counts.datapacks++;
    } else if (type === 'shader') {
      counts.shaders++;
    } else if (type === 'resourcepack') {
      counts.resourcepacks++;
    } else if (type === 'plugin') {
      counts.plugins++;
    } else {
      counts.mods++;
    }
  }

  return counts;
}

export function ServerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: server, isLoading, isError, error } = useServer(id!);
  const startServerMutation = useStartServer();
  const stopServerMutation = useStopServer();
  const deleteServerMutation = useDeleteServer();
  const updateServerMutation = useUpdateServer();

  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const handleStartEdit = () => {
    setEditedName(server?.name || '');
    setIsEditingName(true);
  };

  const handleCancelEdit = () => {
    setIsEditingName(false);
    setEditedName('');
  };

  const handleSaveName = () => {
    if (id && editedName.trim()) {
      updateServerMutation.mutate(
        { serverId: id, data: { name: editedName.trim() } },
        {
          onSuccess: () => {
            setIsEditingName(false);
          },
        }
      );
    }
  };

  const handleStart = () => {
    if (id) {
      startServerMutation.mutate(id);
    }
  };

  const handleStop = () => {
    if (id) {
      stopServerMutation.mutate(id);
    }
  };

  const handleDelete = () => {
    if (id && window.confirm(`Are you sure you want to delete "${server?.name}"? This will remove all server data.`)) {
      deleteServerMutation.mutate(id);
    }
  };

  const handleExportMrpack = async () => {
    if (!id) return;

    setIsExporting(true);
    try {
      await exportServerAsMrpack(id);
    } catch (error: any) {
      console.error('Failed to export modpack:', error);
      alert(error.response?.data?.detail || 'Failed to export server modpack');
    } finally {
      setIsExporting(false);
    }
  };

  const isActionPending = startServerMutation.isPending || stopServerMutation.isPending || deleteServerMutation.isPending;

  // Determine status badge variant
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'default';
      case 'pending':
        return 'secondary';
      case 'stopped':
        return 'outline';
      case 'created':
        return 'outline';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  // Determine if start button should be enabled
  const canStart = server?.status === 'stopped' || server?.status === 'created';

  // Determine if stop button should be enabled
  const canStop = server?.status === 'running' || server?.status === 'pending';

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isError || !server) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" asChild>
          <Link to="/">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Servers
          </Link>
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error instanceof Error ? error.message : 'Server not found'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-9rem)] overflow-hidden gap-6">
      <Button variant="ghost" asChild className="w-fit">
        <Link to="/">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Servers
        </Link>
      </Button>

      <Card className="flex-1 flex flex-col overflow-hidden min-h-0">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center gap-3">
            {isEditingName ? (
              <div className="flex items-center gap-2 flex-1">
                <Input
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="text-3xl font-bold h-auto py-2"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSaveName();
                    } else if (e.key === 'Escape') {
                      handleCancelEdit();
                    }
                  }}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={handleSaveName}
                  disabled={updateServerMutation.isPending || !editedName.trim()}
                >
                  <Check className="h-5 w-5" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={handleCancelEdit}
                  disabled={updateServerMutation.isPending}
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            ) : (
              <>
                <CardTitle className="text-3xl">{server.name}</CardTitle>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={handleStartEdit}
                  className="h-8 w-8"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </>
            )}
            <Badge variant={getStatusVariant(server.status)}>
              {server.status}
            </Badge>
          </div>
          <CardDescription>
            <Badge variant="secondary" className="mr-2">{server.loader}</Badge>
            <span>{server.game_version}</span>
            {(() => {
              const counts = countProjectsByType(server.modrinth_projects);
              const badges = [];
              if (counts.mods > 0) {
                badges.push(
                  <Badge key="mods" variant="outline" className="ml-2">
                    {counts.mods} {counts.mods === 1 ? 'mod' : 'mods'}
                  </Badge>
                );
              }
              if (counts.datapacks > 0) {
                badges.push(
                  <Badge key="datapacks" variant="outline" className="ml-2">
                    {counts.datapacks} {counts.datapacks === 1 ? 'datapack' : 'datapacks'}
                  </Badge>
                );
              }
              if (counts.shaders > 0) {
                badges.push(
                  <Badge key="shaders" variant="outline" className="ml-2">
                    {counts.shaders} {counts.shaders === 1 ? 'shader' : 'shaders'}
                  </Badge>
                );
              }
              if (counts.resourcepacks > 0) {
                badges.push(
                  <Badge key="resourcepacks" variant="outline" className="ml-2">
                    {counts.resourcepacks} {counts.resourcepacks === 1 ? 'resource pack' : 'resource packs'}
                  </Badge>
                );
              }
              if (counts.plugins > 0) {
                badges.push(
                  <Badge key="plugins" variant="outline" className="ml-2">
                    {counts.plugins} {counts.plugins === 1 ? 'plugin' : 'plugins'}
                  </Badge>
                );
              }
              return badges;
            })()}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col overflow-hidden space-y-6">
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden">
            <div className="space-y-6 overflow-y-auto">
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Server ID</h3>
                <p className="font-mono text-sm">{server.id}</p>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Loader</h3>
                <p>{server.loader}</p>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Game Version</h3>
                <p>{server.game_version}</p>
              </div>

              {server.loader === 'fabric' && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-muted-foreground">Modrinth Projects</h3>
                  <InlineModrinthEditor
                    server={server}
                    onUpdate={(projects) =>
                      updateServerMutation.mutate({
                        serverId: server.id,
                        data: { name: server.name, modrinth_projects: projects },
                      })
                    }
                  />
                </div>
              )}

              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Resources</h3>
                <InlineResourceEditor
                  server={server}
                  canEdit={server.status === 'stopped' || server.status === 'created'}
                  onUpdate={(resources) =>
                    updateServerMutation.mutate({
                      serverId: server.id,
                      data: { name: server.name, ...resources },
                    })
                  }
                />
              </div>
            </div>

            <div className="flex flex-col overflow-hidden">
              <ServerLogs serverId={server.id} serverStatus={server.status} />
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-4 border-t flex-shrink-0">
            <Button onClick={handleStart} disabled={isActionPending || !canStart}>
              <Play className="h-4 w-4 mr-2" />
              {startServerMutation.isPending ? 'Starting...' : 'Start Server'}
            </Button>
            <Button onClick={handleStop} variant="secondary" disabled={isActionPending || !canStop}>
              <Square className="h-4 w-4 mr-2" />
              {stopServerMutation.isPending ? 'Stopping...' : 'Stop Server'}
            </Button>
            <Button
              onClick={handleExportMrpack}
              variant="outline"
              disabled={isExporting || !server.modrinth_projects || server.modrinth_projects.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              {isExporting ? 'Exporting...' : 'Export .mrpack'}
            </Button>
            <Button onClick={handleDelete} variant="destructive" disabled={isActionPending}>
              <Trash2 className="h-4 w-4 mr-2" />
              {deleteServerMutation.isPending ? 'Deleting...' : 'Delete Server'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
