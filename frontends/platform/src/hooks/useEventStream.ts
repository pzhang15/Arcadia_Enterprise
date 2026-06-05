import { useCallback, useEffect, useRef, useState } from "react";
import type { StreamEvent } from "../types";

const MAX_EVENTS = 2000;
const RECONNECT_MS = 1500;

export function useEventStream(url: string) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const lastSeqRef = useRef(0);

  const clear = useCallback(() => setEvents([]), []);

  useEffect(() => {
    let closed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (closed) return;
      const sep = url.includes("?") ? "&" : "?";
      const full =
        lastSeqRef.current > 0 ? `${url}${sep}after=${lastSeqRef.current}` : url;
      const es = new EventSource(full);
      esRef.current = es;

      es.onopen = () => setConnected(true);
      es.onerror = () => {
        setConnected(false);
        es.close();
        if (!closed) timer = setTimeout(connect, RECONNECT_MS);
      };

      es.onmessage = (msg) => {
        try {
          const evt = JSON.parse(msg.data) as StreamEvent;
          const seq = (evt as { seq?: number }).seq;
          if (typeof seq === "number") {
            lastSeqRef.current = Math.max(lastSeqRef.current, seq);
          }
          setEvents((prev) => {
            const next = [...prev, evt];
            return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
          });
        } catch {
          /* skip malformed */
        }
      };
    };

    connect();

    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      esRef.current?.close();
      esRef.current = null;
    };
  }, [url]);

  return { events, connected, clear };
}
