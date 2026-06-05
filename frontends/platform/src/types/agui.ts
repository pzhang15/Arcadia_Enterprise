export enum AGUIEventType {
  RUN_STARTED = "RUN_STARTED",
  RUN_FINISHED = "RUN_FINISHED",
  RUN_ERROR = "RUN_ERROR",
  STEP_STARTED = "STEP_STARTED",
  STEP_FINISHED = "STEP_FINISHED",
  TEXT_MESSAGE_START = "TEXT_MESSAGE_START",
  TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT",
  TEXT_MESSAGE_END = "TEXT_MESSAGE_END",
  THINKING_START = "THINKING_START",
  THINKING_CONTENT = "THINKING_CONTENT",
  THINKING_END = "THINKING_END",
  TOOL_CALL_START = "TOOL_CALL_START",
  TOOL_CALL_ARGS = "TOOL_CALL_ARGS",
  TOOL_CALL_END = "TOOL_CALL_END",
  TOOL_CALL_RESULT = "TOOL_CALL_RESULT",
  STATE_SNAPSHOT = "STATE_SNAPSHOT",
  STATE_DELTA = "STATE_DELTA",
  CUSTOM = "CUSTOM",
}

export interface AGUIBaseEvent {
  type: AGUIEventType;
  timestamp: number;
}

export interface RunStartedEvent extends AGUIBaseEvent {
  type: AGUIEventType.RUN_STARTED;
  thread_id: string;
  run_id: string;
}

export interface RunFinishedEvent extends AGUIBaseEvent {
  type: AGUIEventType.RUN_FINISHED;
  thread_id: string;
  run_id: string;
}

export interface RunErrorEvent extends AGUIBaseEvent {
  type: AGUIEventType.RUN_ERROR;
  message: string;
}

export interface StepStartedEvent extends AGUIBaseEvent {
  type: AGUIEventType.STEP_STARTED;
  step_id: string;
  step_name?: string;
}

export interface StepFinishedEvent extends AGUIBaseEvent {
  type: AGUIEventType.STEP_FINISHED;
  step_id: string;
}

export interface TextMessageStartEvent extends AGUIBaseEvent {
  type: AGUIEventType.TEXT_MESSAGE_START;
  message_id: string;
  role: "assistant" | "system";
}

export interface TextMessageContentEvent extends AGUIBaseEvent {
  type: AGUIEventType.TEXT_MESSAGE_CONTENT;
  message_id: string;
  delta: string;
}

export interface TextMessageEndEvent extends AGUIBaseEvent {
  type: AGUIEventType.TEXT_MESSAGE_END;
  message_id: string;
}

export interface ThinkingStartEvent extends AGUIBaseEvent {
  type: AGUIEventType.THINKING_START;
  thinking_id: string;
  step_id?: string;
}

export interface ThinkingContentEvent extends AGUIBaseEvent {
  type: AGUIEventType.THINKING_CONTENT;
  thinking_id: string;
  delta: string;
}

export interface ThinkingEndEvent extends AGUIBaseEvent {
  type: AGUIEventType.THINKING_END;
  thinking_id: string;
}

export interface ToolCallStartEvent extends AGUIBaseEvent {
  type: AGUIEventType.TOOL_CALL_START;
  tool_call_id: string;
  tool_name: string;
  step_id?: string;
}

export interface ToolCallArgsEvent extends AGUIBaseEvent {
  type: AGUIEventType.TOOL_CALL_ARGS;
  tool_call_id: string;
  delta: string;
}

export interface ToolCallEndEvent extends AGUIBaseEvent {
  type: AGUIEventType.TOOL_CALL_END;
  tool_call_id: string;
}

export interface ToolCallResultEvent extends AGUIBaseEvent {
  type: AGUIEventType.TOOL_CALL_RESULT;
  tool_call_id: string;
  result: string;
  exit_code?: number;
}

export interface CustomEvent extends AGUIBaseEvent {
  type: AGUIEventType.CUSTOM;
  name: string;
  value: Record<string, unknown>;
}

export type AGUIEvent =
  | RunStartedEvent
  | RunFinishedEvent
  | RunErrorEvent
  | StepStartedEvent
  | StepFinishedEvent
  | TextMessageStartEvent
  | TextMessageContentEvent
  | TextMessageEndEvent
  | ThinkingStartEvent
  | ThinkingContentEvent
  | ThinkingEndEvent
  | ToolCallStartEvent
  | ToolCallArgsEvent
  | ToolCallEndEvent
  | ToolCallResultEvent
  | CustomEvent;

export interface ToolCallState {
  id: string;
  name: string;
  args: string;
  result?: string;
  exit_code?: number;
  status: "running" | "completed" | "error";
  started_at: number;
  ended_at?: number;
  step_id?: string;
}

export interface MessageBlock {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  toolCalls?: ToolCallState[];
  isStreaming?: boolean;
  stepId?: string;
}

export interface VfsOp {
  op: string;
  path: string;
  source: string;
  bytes: number;
  mount_prefix?: string;
  duration_ms: number;
  timestamp: number;
}

export interface RunStep {
  id: string;
  run_id: string;
  name: string;
  status: "running" | "completed" | "error";
  started_at: number;
  ended_at?: number;
  reasoning: string;
  reasoning_streaming: boolean;
  tool_call_ids: string[];
  message_id?: string;
}

export interface AgentRun {
  id: string;
  thread_id: string;
  status: "running" | "completed" | "error";
  started_at: number;
  ended_at?: number;
  step_ids: string[];
  error?: string;
}
