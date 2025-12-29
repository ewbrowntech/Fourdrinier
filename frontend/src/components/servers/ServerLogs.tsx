import { useEffect, useRef, useState, useMemo } from 'react';
import { getServerLogsUrl } from '@/lib/api/servers';
import { AlertCircle } from 'lucide-react';

interface ServerLogsProps {
  serverId: string;
  serverStatus: string;
}

// Track server sessions to detect restarts
let sessionCounter = 0;
const sessionMap = new Map<string, { status: string; session: number }>();

export function ServerLogs({ serverId, serverStatus }: ServerLogsProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isCancelledRef = useRef(false);

  // Determine if we should show an error based on server status
  const shouldConnect = serverStatus === 'running' || serverStatus === 'pending';

  // Compute session key - increments when transitioning from stopped/created to running/pending
  const sessionKey = useMemo(() => {
    const previous = sessionMap.get(serverId);
    const wasNotRunning = !previous || previous.status === 'stopped' || previous.status === 'created';
    const isNowRunning = shouldConnect;

    if (wasNotRunning && isNowRunning) {
      // Server is restarting - increment session
      sessionCounter++;
      sessionMap.set(serverId, { status: serverStatus, session: sessionCounter });
      return sessionCounter;
    } else {
      // Update status but keep session
      const currentSession = previous?.session ?? 0;
      sessionMap.set(serverId, { status: serverStatus, session: currentSession });
      return currentSession;
    }
  }, [serverId, serverStatus, shouldConnect]);

  // Clear logs when session changes
  useEffect(() => {
    setLogs([]);
    setConnectionError(null);
  }, [sessionKey]);

  // Only show error if there are no logs to display
  const error = !shouldConnect && logs.length === 0 ? 'Server is not running' : connectionError;

  // Manage EventSource connection
  useEffect(() => {
    console.log(`useEffect running - serverStatus: ${serverStatus}, shouldConnect: ${shouldConnect}`);

    // Only connect if server is running or pending
    if (!shouldConnect) {
      // Mark as cancelled and close existing connection
      console.log('Server not running/pending - cancelling connections');
      isCancelledRef.current = true;
      if (reconnectTimeoutRef.current) {
        console.log('Clearing reconnect timeout');
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSourceRef.current) {
        console.log('Closing EventSource');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    // Reset cancellation flag only when we're going to connect
    isCancelledRef.current = false;

    const connect = () => {
      // Double-check we should still be connecting
      if (isCancelledRef.current) {
        console.log('Connect aborted: cancelled');
        return;
      }

      console.log('Connecting to logs stream...');
      const logsUrl = getServerLogsUrl(serverId);
      const eventSource = new EventSource(logsUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setConnectionError(null);
      };

      eventSource.onmessage = (event) => {
        if (event.data) {
          setLogs((prev) => [...prev, event.data]);
        }
      };

      eventSource.onerror = (err) => {
        console.error('EventSource error:', err);
        eventSource.close();

        // Only reconnect if not cancelled
        if (!isCancelledRef.current) {
          console.log('Scheduling reconnect in 2 seconds...');
          // Clear any existing timeout first
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('Reconnect timeout fired');
            reconnectTimeoutRef.current = null;
            connect();
          }, 2000);
        } else {
          console.log('EventSource error but cancelled - not reconnecting');
        }
      };
    };

    connect();

    // Cleanup on unmount or when dependencies change
    return () => {
      console.log('useEffect cleanup running');
      isCancelledRef.current = true;
      if (reconnectTimeoutRef.current) {
        console.log('Cleanup: clearing timeout');
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSourceRef.current) {
        console.log('Cleanup: closing EventSource');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [serverId, shouldConnect, serverStatus]);

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
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
