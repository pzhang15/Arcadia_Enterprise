import { useCallback, useEffect, useRef, useState } from "react";
import type { StreamEvent } from "../types";

const MAX_EVENTS = 2000;

export function useEventStream(url: string) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const clear = useCallback(() => setEvents([]), []);

  useEffect(() => {
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (msg) => {
      try {
        const evt = JSON.parse(msg.data) as StreamEvent;
        setEvents((prev) => {
          const next = [...prev, evt];
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
        });
      } catch {
        /* skip malformed */
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [url]);

  return { events, connected, clear };
}
