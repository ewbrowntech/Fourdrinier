import { useEffect, useRef, useState } from 'react';
import { getServerLogsUrl } from '@/lib/api/servers';
import { AlertCircle } from 'lucide-react';

interface ServerLogsProps {
  serverId: string;
  serverStatus: string;
}

export function ServerLogs({ serverId, serverStatus }: ServerLogsProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  // Determine if we should show an error based on server status
  const shouldConnect = serverStatus === 'running' || serverStatus === 'pending';

  // Only show error if there are no logs to display
  const error = !shouldConnect && logs.length === 0 ? 'Server is not running' : connectionError;
  const showStoppedLine = !shouldConnect && logs.length > 0;

  // Manage EventSource connection
  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof window.setTimeout> | null = null;
    let cancelled = false;

    // Only connect if server is running or pending
    if (!shouldConnect) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return () => {
        cancelled = true;
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
        }
      };
    }

    const connect = () => {
      // Double-check we should still be connecting
      if (cancelled) {
        return;
      }

      const logsUrl = getServerLogsUrl(serverId);
      const eventSource = new EventSource(logsUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setLogs([]);
        setConnectionError(null);
      };

      eventSource.onmessage = (event) => {
        if (event.data) {
          setLogs((prev) => [...prev, event.data]);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();

        // Only reconnect if not cancelled
        if (!cancelled) {
          // Clear any existing timeout first
          if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
          }
          reconnectTimeout = window.setTimeout(() => {
            reconnectTimeout = null;
            connect();
          }, 2000);
        }
      };
    };

    connect();

    // Cleanup on unmount or when dependencies change
    return () => {
      cancelled = true;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [serverId, shouldConnect]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full max-h-full">
      <div className="flex-1 overflow-y-auto bg-slate-950 rounded-md p-4 font-mono text-sm min-h-0">
        {error ? (
          <div className="flex items-center gap-2 text-yellow-500">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-slate-400">Waiting for logs...</div>
        ) : (
          <div className="text-slate-200 whitespace-pre-wrap break-all">
            {logs.map((log, index) => (
              <div key={index} className="mb-1">
                {log}
              </div>
            ))}
            {showStoppedLine ? <div className="mb-1 text-red-400">Server stopped</div> : null}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
