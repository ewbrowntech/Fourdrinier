import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MoreVertical, Play, Square, Trash2, Edit } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { useStartServer } from '@/lib/hooks/useStartServer';
import { useStopServer } from '@/lib/hooks/useStopServer';
import { useDeleteServer } from '@/lib/hooks/useDeleteServer';
import { EditServerDialog } from './EditServerDialog';
import type { Server } from '@/lib/api/types';

interface ServerCardProps {
  server: Server;
}

export function ServerCard({ server }: ServerCardProps) {
  const navigate = useNavigate();
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const startServerMutation = useStartServer();
  const stopServerMutation = useStopServer();
  const deleteServerMutation = useDeleteServer();

  const handleViewDetails = () => {
    navigate(`/servers/${server.id}`);
  };

  const handleStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    startServerMutation.mutate(server.id);
  };

  const handleStop = (e: React.MouseEvent) => {
    e.stopPropagation();
    stopServerMutation.mutate(server.id);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Are you sure you want to delete "${server.name}"? This will remove all server data.`)) {
      deleteServerMutation.mutate(server.id);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditDialogOpen(true);
  };

  const isLoading = startServerMutation.isPending || stopServerMutation.isPending || deleteServerMutation.isPending;

  // Determine status badge variant and text
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
  const canStart = server.status === 'stopped' || server.status === 'created';

  // Determine if stop button should be enabled
  const canStop = server.status === 'running' || server.status === 'pending';

  return (
    <Card className="hover:border-primary/50 transition-colors cursor-pointer" onClick={handleViewDetails}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <CardTitle>{server.name}</CardTitle>
              <Badge variant={getStatusVariant(server.status)}>
                {server.status}
              </Badge>
            </div>
            <CardDescription className="mt-1">
              <Badge variant="secondary" className="mr-2">{server.loader}</Badge>
              <span className="text-sm">{server.game_version}</span>
              {server.modrinth_projects && server.modrinth_projects.length > 0 && (
                <Badge variant="outline" className="ml-2">
                  {server.modrinth_projects.length} {server.modrinth_projects.length === 1 ? 'mod' : 'mods'}
                </Badge>
              )}
            </CardDescription>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" disabled={isLoading}>
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleEdit} disabled={isLoading}>
                <Edit className="h-4 w-4 mr-2" />
                Edit Server
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleStart} disabled={isLoading || !canStart}>
                <Play className="h-4 w-4 mr-2" />
                Start Server
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleStop} disabled={isLoading || !canStop}>
                <Square className="h-4 w-4 mr-2" />
                Stop Server
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleDelete} disabled={isLoading} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Server
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground">
          <span className="font-mono text-xs">{server.id}</span>
        </div>
      </CardContent>
      <EditServerDialog
        server={server}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
      />
    </Card>
  );
}
