import { useCallback, useEffect, useSyncExternalStore } from "react";
import {
  applySessionRunEvent,
  getSessionAbortController,
  getSessionRunSnapshot,
  hydrateSessionRun,
  patchSessionRunState,
  replaceSessionRunState,
  resetSessionAbortController,
  setSessionRunMessages,
  subscribeSessionRun,
} from "@/lib/sessionRunStore";
import { INITIAL_AGENT_STREAM_STATE } from "@/lib/aguiEventReducer";
import type { AGUIEvent, MessageBlock } from "@/types/agui";

export function useAgentStream(sessionId: string | null) {
  const snapshot = useSyncExternalStore(
    (onStoreChange) =>
      sessionId
        ? subscribeSessionRun(sessionId, onStoreChange)
        : () => undefined,
    () =>
      sessionId
        ? getSessionRunSnapshot(sessionId)
        : INITIAL_AGENT_STREAM_STATE,
    () =>
      sessionId
        ? getSessionRunSnapshot(sessionId)
        : INITIAL_AGENT_STREAM_STATE,
  );

  useEffect(() => {
    if (!sessionId) return;
    hydrateSessionRun(sessionId);
  }, [sessionId]);

  const addUserMessage = useCallback(
    (text: string) => {
      if (!sessionId) return;
      const msg: MessageBlock = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: Date.now(),
      };
      const prev = getSessionRunSnapshot(sessionId);
      patchSessionRunState(sessionId, {
        messages: [...prev.messages, msg],
      });
    },
    [sessionId],
  );

  const setMessages = useCallback(
    (msgs: MessageBlock[]) => {
      if (!sessionId) return;
      setSessionRunMessages(sessionId, msgs);
    },
    [sessionId],
  );

  const reset = useCallback(() => {
    if (!sessionId) return;
    getSessionAbortController(sessionId).abort();
    replaceSessionRunState(sessionId, INITIAL_AGENT_STREAM_STATE);
  }, [sessionId]);

  const sendMessage = useCallback(
    async (sid: string, message: string) => {
      const controller = resetSessionAbortController(sid);
      patchSessionRunState(sid, { isStreaming: true, error: null });

      try {
        const res = await fetch(`/api/sessions/${sid}/message/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ message }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `${res.status} ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (!data || data === "[DONE]") continue;

            let event: AGUIEvent;
            try {
              event = JSON.parse(data) as AGUIEvent;
            } catch {
              continue;
            }

            applySessionRunEvent(sid, event);
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          const errorMsg =
            err instanceof Error ? err.message : "Unknown error";
          const prev = getSessionRunSnapshot(sid);
          patchSessionRunState(sid, {
            error: errorMsg,
            messages: [
              ...prev.messages,
              {
                id: `error-${Date.now()}`,
                role: "system",
                content: `Error: ${errorMsg}`,
                timestamp: Date.now(),
              },
            ],
          });
        }
      } finally {
        patchSessionRunState(sid, { isStreaming: false });
      }
    },
    [],
  );

  const abort = useCallback(() => {
    if (!sessionId) return;
    getSessionAbortController(sessionId).abort();
    patchSessionRunState(sessionId, { isStreaming: false });
  }, [sessionId]);

  return {
    messages: snapshot.messages,
    toolCalls: snapshot.toolCalls,
    steps: snapshot.steps,
    runs: snapshot.runs,
    runOrder: snapshot.runOrder,
    vfsOps: snapshot.vfsOps,
    isStreaming: snapshot.isStreaming,
    error: snapshot.error,
    sendMessage,
    addUserMessage,
    setMessages,
    abort,
    reset,
  };
}
