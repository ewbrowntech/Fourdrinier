import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useServer } from '@/lib/hooks/useServer';
import { useStartServer } from '@/lib/hooks/useStartServer';
import { useStopServer } from '@/lib/hooks/useStopServer';
import { useDeleteServer } from '@/lib/hooks/useDeleteServer';
import { useUpdateServer } from '@/lib/hooks/useUpdateServer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Play, Square, Trash2, AlertCircle, Pencil, Check, X, Edit, ExternalLink } from 'lucide-react';
import { ServerLogs } from '@/components/servers/ServerLogs';
import { EditServerDialog } from '@/components/servers/EditServerDialog';
import { getModrinthProjects } from '@/lib/api/modrinth';
import type { ModrinthProjectInfo } from '@/lib/api/types';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export function ServerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: server, isLoading, isError, error } = useServer(id!);
  const startServerMutation = useStartServer();
  const stopServerMutation = useStopServer();
  const deleteServerMutation = useDeleteServer();
  const updateServerMutation = useUpdateServer();

  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [modrinthProjects, setModrinthProjects] = useState<ModrinthProjectInfo[]>([]);

  useEffect(() => {
    if (server?.modrinth_projects && server.modrinth_projects.length > 0) {
      getModrinthProjects(server.modrinth_projects)
        .then(setModrinthProjects)
        .catch((err) => {
          console.error('Failed to fetch enriched project metadata:', err);
          setModrinthProjects([]);
        });
    } else {
      setModrinthProjects([]);
    }
  }, [server?.id, server?.modrinth_projects]);

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
            {server.modrinth_projects && server.modrinth_projects.length > 0 && (
              <Badge variant="outline" className="ml-2">
                {server.modrinth_projects.length} {server.modrinth_projects.length === 1 ? 'mod' : 'mods'}
              </Badge>
            )}
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

              {modrinthProjects.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-muted-foreground">Mods</h3>
                  <TooltipProvider>
                    <div className="flex flex-wrap gap-2">
                      {modrinthProjects.map((project) => {
                        const modrinthUrl = `https://modrinth.com/mod/${project.project_id}`;

                        return (
                          <Tooltip key={project.project_id}>
                            <TooltipTrigger asChild>
                              <div
                                className={cn(
                                  'px-2 py-1 rounded-md text-xs bg-secondary text-secondary-foreground cursor-default'
                                )}
                              >
                                <span>{project.title}</span>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <a
                                href={modrinthUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-xs hover:underline"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="h-3 w-3" />
                                Modrinth
                              </a>
                            </TooltipContent>
                          </Tooltip>
                        );
                      })}
                    </div>
                  </TooltipProvider>
                </div>
              )}
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
            <Button onClick={() => setEditDialogOpen(true)} variant="outline" disabled={isActionPending}>
              <Edit className="h-4 w-4 mr-2" />
              Edit Server
            </Button>
            <Button onClick={handleDelete} variant="destructive" disabled={isActionPending}>
              <Trash2 className="h-4 w-4 mr-2" />
              {deleteServerMutation.isPending ? 'Deleting...' : 'Delete Server'}
            </Button>
          </div>
        </CardContent>
      </Card>
      <EditServerDialog
        server={server}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
      />
    </div>
  );
}
