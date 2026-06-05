import {
  AGUIEventType,
  type AGUIEvent,
  type AgentRun,
  type MessageBlock,
  type RunStep,
  type ToolCallState,
  type VfsOp,
} from "@/types/agui";

export interface AgentStreamState {
  messages: MessageBlock[];
  toolCalls: Record<string, ToolCallState>;
  steps: Record<string, RunStep>;
  runs: Record<string, AgentRun>;
  runOrder: string[];
  vfsOps: VfsOp[];
  isStreaming: boolean;
  error: string | null;
}

export const INITIAL_AGENT_STREAM_STATE: AgentStreamState = {
  messages: [],
  toolCalls: {},
  steps: {},
  runs: {},
  runOrder: [],
  vfsOps: [],
  isStreaming: false,
  error: null,
};

export interface ReducerRefs {
  currentRunId: string | null;
  currentStepId: string | null;
  currentThinkingStep: string | null;
  messageBuffers: Map<string, string>;
  thinkingBuffers: Map<string, string>;
}

export function createReducerRefs(): ReducerRefs {
  return {
    currentRunId: null,
    currentStepId: null,
    currentThinkingStep: null,
    messageBuffers: new Map(),
    thinkingBuffers: new Map(),
  };
}

export function applyAguiEvent(
  prev: AgentStreamState,
  event: AGUIEvent,
  refs: ReducerRefs,
): AgentStreamState {
  switch (event.type) {
    case AGUIEventType.RUN_STARTED: {
      refs.currentRunId = event.run_id;
      return {
        ...prev,
        runs: {
          ...prev.runs,
          [event.run_id]: {
            id: event.run_id,
            thread_id: event.thread_id,
            status: "running",
            started_at: event.timestamp,
            step_ids: [],
          },
        },
        runOrder: prev.runOrder.includes(event.run_id)
          ? prev.runOrder
          : [...prev.runOrder, event.run_id],
      };
    }

    case AGUIEventType.RUN_FINISHED: {
      const run = prev.runs[event.run_id];
      refs.currentRunId = null;
      if (!run) return prev;
      return {
        ...prev,
        runs: {
          ...prev.runs,
          [event.run_id]: {
            ...run,
            status: "completed",
            ended_at: event.timestamp,
          },
        },
      };
    }

    case AGUIEventType.STEP_STARTED: {
      const runId = refs.currentRunId || "run-implicit";
      const stepId = event.step_id;
      refs.currentStepId = stepId;
      const step: RunStep = {
        id: stepId,
        run_id: runId,
        name: event.step_name || stepId,
        status: "running",
        started_at: event.timestamp,
        reasoning: "",
        reasoning_streaming: false,
        tool_call_ids: [],
      };
      const runs = { ...prev.runs };
      if (runs[runId]) {
        runs[runId] = {
          ...runs[runId],
          step_ids: runs[runId].step_ids.includes(stepId)
            ? runs[runId].step_ids
            : [...runs[runId].step_ids, stepId],
        };
      }
      return {
        ...prev,
        steps: { ...prev.steps, [stepId]: step },
        runs,
      };
    }

    case AGUIEventType.STEP_FINISHED: {
      const step = prev.steps[event.step_id];
      if (refs.currentStepId === event.step_id) {
        refs.currentStepId = null;
      }
      if (!step) return prev;
      return {
        ...prev,
        steps: {
          ...prev.steps,
          [event.step_id]: {
            ...step,
            status: "completed",
            ended_at: event.timestamp,
            reasoning_streaming: false,
          },
        },
      };
    }

    case AGUIEventType.THINKING_START: {
      const stepId = event.step_id || refs.currentStepId;
      if (!stepId) return prev;
      refs.currentThinkingStep = stepId;
      refs.thinkingBuffers.set(event.thinking_id, "");
      const step = prev.steps[stepId];
      if (!step) return prev;
      return {
        ...prev,
        steps: {
          ...prev.steps,
          [stepId]: { ...step, reasoning_streaming: true },
        },
      };
    }

    case AGUIEventType.THINKING_CONTENT: {
      const stepId = refs.currentThinkingStep;
      if (!stepId) return prev;
      const cur = refs.thinkingBuffers.get(event.thinking_id) || "";
      const next = cur + event.delta;
      refs.thinkingBuffers.set(event.thinking_id, next);
      const step = prev.steps[stepId];
      if (!step) return prev;
      return {
        ...prev,
        steps: {
          ...prev.steps,
          [stepId]: { ...step, reasoning: step.reasoning + event.delta },
        },
      };
    }

    case AGUIEventType.THINKING_END: {
      const stepId = refs.currentThinkingStep;
      refs.currentThinkingStep = null;
      if (!stepId) return prev;
      const step = prev.steps[stepId];
      if (!step) return prev;
      return {
        ...prev,
        steps: {
          ...prev.steps,
          [stepId]: { ...step, reasoning_streaming: false },
        },
      };
    }

    case AGUIEventType.TEXT_MESSAGE_START: {
      const stepId = refs.currentStepId || undefined;
      refs.messageBuffers.set(event.message_id, "");
      const newMsg: MessageBlock = {
        id: event.message_id,
        role: event.role === "system" ? "system" : "assistant",
        content: "",
        timestamp: event.timestamp,
        toolCalls: [],
        isStreaming: true,
        stepId,
      };
      const next: AgentStreamState = {
        ...prev,
        messages: [...prev.messages, newMsg],
      };
      if (stepId && prev.steps[stepId]) {
        next.steps = {
          ...prev.steps,
          [stepId]: { ...prev.steps[stepId], message_id: event.message_id },
        };
      }
      return next;
    }

    case AGUIEventType.TEXT_MESSAGE_CONTENT: {
      const cur = refs.messageBuffers.get(event.message_id) || "";
      const next = cur + event.delta;
      refs.messageBuffers.set(event.message_id, next);
      return {
        ...prev,
        messages: prev.messages.map((m) =>
          m.id === event.message_id
            ? { ...m, content: next, isStreaming: true }
            : m,
        ),
      };
    }

    case AGUIEventType.TEXT_MESSAGE_END: {
      refs.messageBuffers.delete(event.message_id);
      return {
        ...prev,
        messages: prev.messages.map((m) =>
          m.id === event.message_id ? { ...m, isStreaming: false } : m,
        ),
      };
    }

    case AGUIEventType.TOOL_CALL_START: {
      const stepId = event.step_id || refs.currentStepId || undefined;
      const tc: ToolCallState = {
        id: event.tool_call_id,
        name: event.tool_name,
        args: "",
        status: "running",
        started_at: event.timestamp,
        step_id: stepId,
      };
      const next: AgentStreamState = {
        ...prev,
        toolCalls: { ...prev.toolCalls, [tc.id]: tc },
      };
      if (stepId && prev.steps[stepId]) {
        next.steps = {
          ...prev.steps,
          [stepId]: {
            ...prev.steps[stepId],
            tool_call_ids: prev.steps[stepId].tool_call_ids.includes(tc.id)
              ? prev.steps[stepId].tool_call_ids
              : [...prev.steps[stepId].tool_call_ids, tc.id],
          },
        };
      }
      return next;
    }

    case AGUIEventType.TOOL_CALL_ARGS: {
      const existing = prev.toolCalls[event.tool_call_id];
      if (!existing) return prev;
      return {
        ...prev,
        toolCalls: {
          ...prev.toolCalls,
          [event.tool_call_id]: {
            ...existing,
            args: existing.args + event.delta,
          },
        },
      };
    }

    case AGUIEventType.TOOL_CALL_END: {
      const existing = prev.toolCalls[event.tool_call_id];
      if (!existing) return prev;
      return {
        ...prev,
        toolCalls: {
          ...prev.toolCalls,
          [event.tool_call_id]: {
            ...existing,
            status: existing.status === "error" ? "error" : "completed",
            ended_at: event.timestamp,
          },
        },
      };
    }

    case AGUIEventType.TOOL_CALL_RESULT: {
      const existing = prev.toolCalls[event.tool_call_id];
      if (!existing) return prev;
      return {
        ...prev,
        toolCalls: {
          ...prev.toolCalls,
          [event.tool_call_id]: {
            ...existing,
            result: event.result,
            exit_code: event.exit_code,
            status:
              event.exit_code !== undefined && event.exit_code !== 0
                ? "error"
                : "completed",
            ended_at: existing.ended_at || event.timestamp,
          },
        },
      };
    }

    case AGUIEventType.CUSTOM: {
      if (event.name === "vfs_op") {
        const op = event.value as unknown as VfsOp;
        return {
          ...prev,
          vfsOps: [...prev.vfsOps, { ...op, timestamp: event.timestamp }],
        };
      }
      return prev;
    }

    case AGUIEventType.RUN_ERROR: {
      return { ...prev, error: event.message };
    }

    default:
      return prev;
  }
}

export function replayAguiEvents(events: AGUIEvent[]): AgentStreamState {
  const refs = createReducerRefs();
  let state = INITIAL_AGENT_STREAM_STATE;
  for (const event of events) {
    state = applyAguiEvent(state, event, refs);
  }
  return { ...state, isStreaming: false };
}

export function messagesFromChatHistory(
  sessionId: string,
  history: { role: string; content: string; timestamp: number }[],
): MessageBlock[] {
  return history.map((h, idx) => ({
    id: `${sessionId}-${h.timestamp}-${idx}`,
    role:
      h.role === "user"
        ? "user"
        : h.role === "system"
          ? "system"
          : "assistant",
    content: h.content,
    timestamp: h.timestamp * 1000,
  }));
}
