import { beforeEach, describe, expect, it } from "vitest";
import { AGUIEventType } from "@/types/agui";
import {
  applySessionRunEvent,
  beginSessionStream,
  getSessionRunSnapshot,
  replaceSessionRunState,
  clearSessionRun,
} from "../sessionRunStore";
import { INITIAL_AGENT_STREAM_STATE } from "../aguiEventReducer";

const STORAGE_KEY = "arcadia.session-run.v1";

describe("sessionRunStore", () => {
  beforeEach(() => {
    clearSessionRun("test-sess");
    localStorage.clear();
  });

  it("accumulates streamed message content across events", () => {
    beginSessionStream("test-sess");
    replaceSessionRunState("test-sess", INITIAL_AGENT_STREAM_STATE);
    applySessionRunEvent("test-sess", {
      type: AGUIEventType.TEXT_MESSAGE_START,
      timestamp: 1,
      message_id: "m1",
      role: "assistant",
    });
    applySessionRunEvent("test-sess", {
      type: AGUIEventType.TEXT_MESSAGE_CONTENT,
      timestamp: 2,
      message_id: "m1",
      delta: "Part ",
    });
    applySessionRunEvent("test-sess", {
      type: AGUIEventType.TEXT_MESSAGE_CONTENT,
      timestamp: 3,
      message_id: "m1",
      delta: "one",
    });
    expect(getSessionRunSnapshot("test-sess").messages[0]?.content).toBe(
      "Part one",
    );
  });

  it("applies events into shared session state", () => {
    replaceSessionRunState("test-sess", INITIAL_AGENT_STREAM_STATE);
    applySessionRunEvent("test-sess", {
      type: AGUIEventType.RUN_STARTED,
      timestamp: 1,
      thread_id: "test-sess",
      run_id: "run-a",
    });
    const snap = getSessionRunSnapshot("test-sess");
    expect(snap.runOrder).toEqual(["run-a"]);
  });

  it("writes session state to localStorage", async () => {
    replaceSessionRunState("test-sess", {
      ...INITIAL_AGENT_STREAM_STATE,
      messages: [
        {
          id: "m1",
          role: "user",
          content: "hello",
          timestamp: 1,
        },
      ],
    });
    await new Promise((r) => setTimeout(r, 450));
    const raw = localStorage.getItem(STORAGE_KEY);
    expect(raw).toContain("hello");
  });
});
