import { useCallback, useRef, useState } from "react";
import {
  AGUIEventType,
  type AGUIEvent,
  type MessageBlock,
  type ToolCallState,
  type VfsOp,
} from "@/types/agui";

interface AgentStreamState {
  messages: MessageBlock[];
  vfsOps: VfsOp[];
  isStreaming: boolean;
  error: string | null;
}

export function useAgentStream() {
  const [state, setState] = useState<AgentStreamState>({
    messages: [],
    vfsOps: [],
    isStreaming: false,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const currentMessageRef = useRef<string>("");
  const toolCallsRef = useRef<Map<string, ToolCallState>>(new Map());

  const addUserMessage = useCallback((text: string) => {
    const msg: MessageBlock = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setState((prev) => ({ ...prev, messages: [...prev.messages, msg] }));
  }, []);

  const setMessages = useCallback((msgs: MessageBlock[]) => {
    setState((prev) => ({ ...prev, messages: msgs }));
  }, []);

  const sendMessage = useCallback(
    async (sessionId: string, message: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      currentMessageRef.current = "";
      toolCallsRef.current = new Map();

      setState((prev) => ({ ...prev, isStreaming: true, error: null }));

      try {
        const res = await fetch(`/api/sessions/${sessionId}/message/stream`, {
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
        let assistantMsgId = "";

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

            switch (event.type) {
              case AGUIEventType.TEXT_MESSAGE_START: {
                assistantMsgId = event.message_id;
                currentMessageRef.current = "";
                const newMsg: MessageBlock = {
                  id: assistantMsgId,
                  role: event.role === "system" ? "system" : "assistant",
                  content: "",
                  timestamp: event.timestamp,
                  toolCalls: [],
                  isStreaming: true,
                };
                setState((prev) => ({
                  ...prev,
                  messages: [...prev.messages, newMsg],
                }));
                break;
              }

              case AGUIEventType.TEXT_MESSAGE_CONTENT: {
                currentMessageRef.current += event.delta;
                const content = currentMessageRef.current;
                const calls = Array.from(toolCallsRef.current.values());
                setState((prev) => ({
                  ...prev,
                  messages: prev.messages.map((m) =>
                    m.id === event.message_id
                      ? { ...m, content, toolCalls: calls, isStreaming: true }
                      : m,
                  ),
                }));
                break;
              }

              case AGUIEventType.TEXT_MESSAGE_END: {
                const finalContent = currentMessageRef.current;
                const finalCalls = Array.from(toolCallsRef.current.values());
                setState((prev) => ({
                  ...prev,
                  messages: prev.messages.map((m) =>
                    m.id === event.message_id
                      ? {
                          ...m,
                          content: finalContent,
                          toolCalls: finalCalls,
                          isStreaming: false,
                        }
                      : m,
                  ),
                }));
                break;
              }

              case AGUIEventType.TOOL_CALL_START: {
                const tc: ToolCallState = {
                  id: event.tool_call_id,
                  name: event.tool_name,
                  args: "",
                  status: "running",
                };
                toolCallsRef.current.set(event.tool_call_id, tc);
                break;
              }

              case AGUIEventType.TOOL_CALL_ARGS: {
                const existing = toolCallsRef.current.get(event.tool_call_id);
                if (existing) {
                  existing.args += event.delta;
                }
                break;
              }

              case AGUIEventType.TOOL_CALL_END: {
                const tc = toolCallsRef.current.get(event.tool_call_id);
                if (tc) tc.status = "completed";
                break;
              }

              case AGUIEventType.TOOL_CALL_RESULT: {
                const tc = toolCallsRef.current.get(event.tool_call_id);
                if (tc) {
                  tc.result = event.result;
                  tc.exit_code = event.exit_code;
                  tc.status =
                    event.exit_code !== undefined && event.exit_code !== 0
                      ? "error"
                      : "completed";
                }
                const updatedCalls = Array.from(toolCallsRef.current.values());
                setState((prev) => ({
                  ...prev,
                  messages: prev.messages.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, toolCalls: updatedCalls }
                      : m,
                  ),
                }));
                break;
              }

              case AGUIEventType.CUSTOM: {
                if (event.name === "vfs_op") {
                  const op = event.value as unknown as VfsOp;
                  setState((prev) => ({
                    ...prev,
                    vfsOps: [...prev.vfsOps, { ...op, timestamp: event.timestamp }],
                  }));
                }
                break;
              }

              case AGUIEventType.RUN_ERROR: {
                setState((prev) => ({ ...prev, error: event.message }));
                break;
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          const errorMsg =
            err instanceof Error ? err.message : "Unknown error";
          setState((prev) => ({
            ...prev,
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
          }));
        }
      } finally {
        setState((prev) => ({ ...prev, isStreaming: false }));
      }
    },
    [],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  const clearVfsOps = useCallback(() => {
    setState((prev) => ({ ...prev, vfsOps: [] }));
  }, []);

  return {
    messages: state.messages,
    vfsOps: state.vfsOps,
    isStreaming: state.isStreaming,
    error: state.error,
    sendMessage,
    addUserMessage,
    setMessages,
    abort,
    clearVfsOps,
  };
}
