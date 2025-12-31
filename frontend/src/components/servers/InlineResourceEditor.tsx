import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Pencil, X, Check, AlertCircle } from 'lucide-react';
import type { Server } from '@/lib/api/types';
import { toast } from 'sonner';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface InlineResourceEditorProps {
  server: Server;
  canEdit: boolean;
  onUpdate: (resources: {
    cpu_request?: string | null;
    cpu_limit?: string | null;
    memory_request?: string | null;
    memory_limit?: string | null;
  }) => void;
}

export function InlineResourceEditor({ server, canEdit, onUpdate }: InlineResourceEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [cpuRequest, setCpuRequest] = useState('');
  const [cpuLimit, setCpuLimit] = useState('');
  const [memoryRequest, setMemoryRequest] = useState('');
  const [memoryLimit, setMemoryLimit] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isEditing) {
      setCpuRequest(server.cpu_request || '');
      setCpuLimit(server.cpu_limit || '');
      setMemoryRequest(server.memory_request || '');
      setMemoryLimit(server.memory_limit || '');
    }
  }, [server, isEditing]);

  const validateCpu = (value: string): string | null => {
    if (!value) return null;
    if (!/^\d+m?$/.test(value)) {
      return 'Format: 1000m or 1';
    }
    return null;
  };

  const validateMemory = (value: string): string | null => {
    if (!value) return null;
    if (!/^\d+(Mi|Gi)$/.test(value)) {
      return 'Format: 2Gi or 512Mi';
    }
    return null;
  };

  const handleEdit = () => {
    if (!canEdit) {
      toast.error('Stop the server to edit resources');
      return;
    }
    setErrors({});
    setIsEditing(true);
  };

  const handleCancel = () => {
    setCpuRequest(server.cpu_request || '');
    setCpuLimit(server.cpu_limit || '');
    setMemoryRequest(server.memory_request || '');
    setMemoryLimit(server.memory_limit || '');
    setErrors({});
    setIsEditing(false);
  };

  const handleSave = () => {
    const nextErrors: Record<string, string> = {};

    if (cpuRequest) {
      const error = validateCpu(cpuRequest);
      if (error) nextErrors.cpuRequest = error;
    }
    if (cpuLimit) {
      const error = validateCpu(cpuLimit);
      if (error) nextErrors.cpuLimit = error;
    }
    if (memoryRequest) {
      const error = validateMemory(memoryRequest);
      if (error) nextErrors.memoryRequest = error;
    }
    if (memoryLimit) {
      const error = validateMemory(memoryLimit);
      if (error) nextErrors.memoryLimit = error;
    }

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      toast.error('Please fix validation errors');
      return;
    }

    onUpdate({
      cpu_request: cpuRequest || null,
      cpu_limit: cpuLimit || null,
      memory_request: memoryRequest || null,
      memory_limit: memoryLimit || null,
    });
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <div className="flex items-center justify-between">
        <div className="space-y-1 text-sm flex-1">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">CPU:</span>
            <span>
              {server.cpu_request || 'default'} / {server.cpu_limit || 'default'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Memory:</span>
            <span>
              {server.memory_request || 'default'} / {server.memory_limit || 'default'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Storage:</span>
            <span>{server.pvc_size || 'default'}</span>
          </div>
        </div>
        {canEdit ? (
          <Button variant="ghost" size="sm" onClick={handleEdit}>
            <Pencil className="h-3 w-3" />
          </Button>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="p-2">
                  <AlertCircle className="h-4 w-4 text-muted-foreground" />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Stop the server to edit resources</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3 border rounded-lg p-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="cpuRequest" className="text-xs">
            CPU Request
          </Label>
          <Input
            id="cpuRequest"
            value={cpuRequest}
            onChange={(e) => setCpuRequest(e.target.value)}
            placeholder="e.g., 1000m"
            className={errors.cpuRequest ? 'border-destructive' : ''}
          />
          {errors.cpuRequest ? (
            <p className="text-xs text-destructive mt-1">{errors.cpuRequest}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Format: 1000m or 1</p>
          )}
        </div>
        <div>
          <Label htmlFor="cpuLimit" className="text-xs">
            CPU Limit
          </Label>
          <Input
            id="cpuLimit"
            value={cpuLimit}
            onChange={(e) => setCpuLimit(e.target.value)}
            placeholder="e.g., 2000m"
            className={errors.cpuLimit ? 'border-destructive' : ''}
          />
          {errors.cpuLimit ? (
            <p className="text-xs text-destructive mt-1">{errors.cpuLimit}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Format: 2000m or 2</p>
          )}
        </div>
        <div>
          <Label htmlFor="memoryRequest" className="text-xs">
            Memory Request
          </Label>
          <Input
            id="memoryRequest"
            value={memoryRequest}
            onChange={(e) => setMemoryRequest(e.target.value)}
            placeholder="e.g., 2Gi"
            className={errors.memoryRequest ? 'border-destructive' : ''}
          />
          {errors.memoryRequest ? (
            <p className="text-xs text-destructive mt-1">{errors.memoryRequest}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Format: 2Gi or 512Mi</p>
          )}
        </div>
        <div>
          <Label htmlFor="memoryLimit" className="text-xs">
            Memory Limit
          </Label>
          <Input
            id="memoryLimit"
            value={memoryLimit}
            onChange={(e) => setMemoryLimit(e.target.value)}
            placeholder="e.g., 4Gi"
            className={errors.memoryLimit ? 'border-destructive' : ''}
          />
          {errors.memoryLimit ? (
            <p className="text-xs text-destructive mt-1">{errors.memoryLimit}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Format: 4Gi or 1024Mi</p>
          )}
        </div>
      </div>

      <div>
        <Label className="text-xs">PVC Size</Label>
        <div className="text-sm py-2">{server.pvc_size || 'default (from config)'}</div>
        <p className="text-xs text-muted-foreground">Cannot be changed after creation</p>
      </div>

      {/* Save/Cancel buttons */}
      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={handleSave}>
          <Check className="h-3 w-3 mr-1" />
          Save
        </Button>
        <Button size="sm" variant="outline" onClick={handleCancel}>
          <X className="h-3 w-3 mr-1" />
          Cancel
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        Leave fields empty to use default values from configuration
      </p>
    </div>
  );
}
