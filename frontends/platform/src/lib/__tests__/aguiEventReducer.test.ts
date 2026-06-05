import { describe, expect, it } from "vitest";
import { AGUIEventType } from "@/types/agui";
import { applyAguiEvent, createReducerRefs, replayAguiEvents } from "../aguiEventReducer";

describe("replayAguiEvents", () => {
  it("rebuilds runs, steps, tools, and messages from a trace", () => {
    const ts = 1_700_000_000_000;
    const state = replayAguiEvents([
      {
        type: AGUIEventType.RUN_STARTED,
        timestamp: ts,
        thread_id: "sess-1",
        run_id: "run-1",
      },
      {
        type: AGUIEventType.STEP_STARTED,
        timestamp: ts + 1,
        step_id: "step-1",
        step_name: "Analyze",
      },
      {
        type: AGUIEventType.TOOL_CALL_START,
        timestamp: ts + 2,
        tool_call_id: "tc-1",
        tool_name: "exec",
        step_id: "step-1",
      },
      {
        type: AGUIEventType.TOOL_CALL_ARGS,
        timestamp: ts + 3,
        tool_call_id: "tc-1",
        delta: "ls /tickets",
      },
      {
        type: AGUIEventType.TOOL_CALL_RESULT,
        timestamp: ts + 4,
        tool_call_id: "tc-1",
        result: "ok",
        exit_code: 0,
      },
      {
        type: AGUIEventType.TOOL_CALL_END,
        timestamp: ts + 5,
        tool_call_id: "tc-1",
      },
      {
        type: AGUIEventType.TEXT_MESSAGE_START,
        timestamp: ts + 6,
        message_id: "msg-1",
        role: "assistant",
      },
      {
        type: AGUIEventType.TEXT_MESSAGE_CONTENT,
        timestamp: ts + 7,
        message_id: "msg-1",
        delta: "Done.",
      },
      {
        type: AGUIEventType.TEXT_MESSAGE_END,
        timestamp: ts + 8,
        message_id: "msg-1",
      },
      {
        type: AGUIEventType.STEP_FINISHED,
        timestamp: ts + 9,
        step_id: "step-1",
      },
      {
        type: AGUIEventType.RUN_FINISHED,
        timestamp: ts + 10,
        thread_id: "sess-1",
        run_id: "run-1",
      },
    ]);

    expect(state.runOrder).toEqual(["run-1"]);
    expect(state.steps["step-1"]?.tool_call_ids).toContain("tc-1");
    expect(state.toolCalls["tc-1"]?.result).toBe("ok");
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0]?.content).toBe("Done.");
    expect(state.isStreaming).toBe(false);
  });

  it("accumulates streaming text deltas with persistent refs", () => {
    const refs = createReducerRefs();
    let state = replayAguiEvents([]);
    state = applyAguiEvent(state, {
      type: AGUIEventType.TEXT_MESSAGE_START,
      timestamp: 1,
      message_id: "msg-1",
      role: "assistant",
    }, refs);
    state = applyAguiEvent(state, {
      type: AGUIEventType.TEXT_MESSAGE_CONTENT,
      timestamp: 2,
      message_id: "msg-1",
      delta: "Hel",
    }, refs);
    state = applyAguiEvent(state, {
      type: AGUIEventType.TEXT_MESSAGE_CONTENT,
      timestamp: 3,
      message_id: "msg-1",
      delta: "lo",
    }, refs);
    expect(state.messages[0]?.content).toBe("Hello");
  });
});
