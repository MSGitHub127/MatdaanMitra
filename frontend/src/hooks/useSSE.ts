import { useEffect, useState, useRef } from 'react';

interface SSEOptions {
  url: string;
  headers?: Record<string, string>;
  onMessage?: (data: any) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
}

export function useSSE({ url, headers = {}, onMessage, onError, onClose }: SSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (error) => {
      setIsConnected(false);
      onError?.(new Error('SSE connection error'));
      eventSource.close();
    };

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
      onClose?.();
    };
  }, [url, headers, onMessage, onError, onClose]);

  return { isConnected };
}
