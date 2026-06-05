from __future__ import annotations

from typing import Any

from arcadia_store.types import (EventRow, FeedOut, RunRow, StepRow,
                                 ToolCallRow, VfsOpRow)


class StreamCoalescer:
    """Folds a live AG-UI event stream into the minimal set of rows to persist.

    Per-token delta events (TEXT_MESSAGE_CONTENT / THINKING_CONTENT / TOOL_CALL_ARGS)
    are accumulated in memory and emitted as a single consolidated event at their END
    boundary. Because the frontend reducer reconstructs content as ``buffer + delta``
    from empty, one full-text event replays byte-identically to N deltas. Structural
    events pass through verbatim. Derived run/step/tool_call/vfs_op rows are produced
    alongside for fast querying.

    Args:
        session_id (str): The session these events belong to.
        start_seq (int): First per-session sequence number to assign (max(seq)+1).
    """

    def __init__(self, session_id: str, start_seq: int) -> None:
        self._session_id = session_id
        self._seq = start_seq
        self._msg: dict[str, dict[str, Any]] = {}
        self._think: dict[str, dict[str, Any]] = {}
        self._tool: dict[str, dict[str, Any]] = {}
        self._cur_run: str | None = None
        self._cur_step: str | None = None
        self._runs: dict[str, RunRow] = {}
        self._steps: dict[str, StepRow] = {}
        self._tools: dict[str, ToolCallRow] = {}

    @property
    def next_seq(self) -> int:
        return self._seq

    def _next(self) -> int:
        s = self._seq
        self._seq += 1
        return s

    def _row(self, ev: dict, run_id: str | None,
             step_id: str | None) -> EventRow:
        return EventRow(
            session_id=self._session_id,
            seq=self._next(),
            type=ev.get("type", ""),
            payload=ev,
            timestamp_ms=int(ev.get("timestamp") or 0),
            run_id=run_id,
            step_id=step_id,
        )

    def feed(self, ev: dict) -> FeedOut:
        """Process one live event, returning rows to buffer for persistence.

        Args:
            ev (dict): A raw AG-UI event dict as yielded by the agent stream.

        Returns:
            FeedOut: Consolidated events plus any derived rows.
        """
        t = ev.get("type")
        ts = int(ev.get("timestamp") or 0)
        out = FeedOut()
        if t == "RUN_STARTED":
            self._cur_run = ev.get("run_id")
            run = RunRow(run_id=self._cur_run,
                         session_id=self._session_id,
                         status="running",
                         started_at_ms=ts)
            self._runs[self._cur_run] = run
            out.events.append(self._row(ev, self._cur_run, None))
            out.runs.append(run)
        elif t in ("RUN_FINISHED", "RUN_ERROR"):
            rid = ev.get("run_id") or self._cur_run
            out.events.append(self._row(ev, rid, None))
            if rid:
                run = self._runs.get(rid) or RunRow(
                    run_id=rid,
                    session_id=self._session_id,
                    status="running",
                    started_at_ms=ts)
                run.status = "error" if t == "RUN_ERROR" else "completed"
                run.ended_at_ms = ts
                if t == "RUN_ERROR":
                    run.error = ev.get("message") or ev.get("error")
                self._runs[rid] = run
                out.runs.append(run)
        elif t == "STEP_STARTED":
            self._cur_step = ev.get("step_id")
            step = StepRow(step_id=self._cur_step,
                           run_id=self._cur_run,
                           session_id=self._session_id,
                           name=ev.get("step_name") or "",
                           status="running",
                           started_at_ms=ts)
            self._steps[self._cur_step] = step
            out.events.append(self._row(ev, self._cur_run, self._cur_step))
            out.steps.append(step)
        elif t == "STEP_FINISHED":
            sid = ev.get("step_id")
            out.events.append(self._row(ev, self._cur_run, sid))
            step = self._steps.get(sid)
            if step is not None:
                step.status = "completed"
                step.ended_at_ms = ts
                out.steps.append(step)
        elif t == "TEXT_MESSAGE_START":
            mid = ev.get("message_id")
            self._msg[mid] = {
                "content": "",
                "ts": ts,
                "step_id": self._cur_step,
                "start": ev
            }
            step = self._steps.get(self._cur_step)
            if step is not None and not step.message_id:
                step.message_id = mid
                out.steps.append(step)
        elif t == "TEXT_MESSAGE_CONTENT":
            b = self._msg.get(ev.get("message_id"))
            if b is not None:
                b["content"] += ev.get("delta") or ""
            else:
                out.events.append(self._row(ev, self._cur_run, self._cur_step))
        elif t == "TEXT_MESSAGE_END":
            out.events.extend(self._flush_text(ev.get("message_id"), ev))
        elif t == "THINKING_START":
            tid = ev.get("thinking_id")
            self._think[tid] = {
                "content": "",
                "ts": ts,
                "step_id": ev.get("step_id") or self._cur_step,
                "start": ev
            }
        elif t == "THINKING_CONTENT":
            b = self._think.get(ev.get("thinking_id"))
            if b is not None:
                b["content"] += ev.get("delta") or ""
            else:
                out.events.append(self._row(ev, self._cur_run, self._cur_step))
        elif t == "THINKING_END":
            rows, step = self._flush_thinking(ev.get("thinking_id"), ev)
            out.events.extend(rows)
            if step is not None:
                out.steps.append(step)
        elif t == "TOOL_CALL_START":
            tcid = ev.get("tool_call_id")
            self._tool[tcid] = {"args": "", "ts": ts, "start": ev}
            tool = ToolCallRow(tool_call_id=tcid,
                               session_id=self._session_id,
                               run_id=self._cur_run,
                               step_id=self._cur_step,
                               tool_name=ev.get("tool_name") or "",
                               status="running",
                               started_at_ms=ts)
            self._tools[tcid] = tool
            out.tool_calls.append(tool)
        elif t == "TOOL_CALL_ARGS":
            b = self._tool.get(ev.get("tool_call_id"))
            if b is not None:
                b["args"] += ev.get("delta") or ""
            else:
                out.events.append(self._row(ev, self._cur_run, self._cur_step))
        elif t == "TOOL_CALL_END":
            tcid = ev.get("tool_call_id")
            out.events.extend(self._flush_tool(tcid, ev))
            tool = self._tools.get(tcid)
            if tool is not None:
                out.tool_calls.append(tool)
        elif t == "TOOL_CALL_RESULT":
            tcid = ev.get("tool_call_id")
            out.events.append(self._row(ev, self._cur_run, self._cur_step))
            tool = self._tools.get(tcid)
            if tool is not None:
                tool.result = ev.get("result")
                tool.exit_code = ev.get("exit_code")
                failed = (ev.get("exit_code") or 0) != 0
                tool.status = "error" if failed else "completed"
                tool.ended_at_ms = ts
                out.tool_calls.append(tool)
        elif t == "CUSTOM":
            out.events.append(self._row(ev, self._cur_run, self._cur_step))
            if ev.get("name") == "vfs_op":
                v = ev.get("value") or {}
                out.vfs_ops.append(
                    VfsOpRow(session_id=self._session_id,
                             op=v.get("op") or "",
                             path=v.get("path") or "",
                             source=v.get("source") or "",
                             bytes=int(v.get("bytes") or 0),
                             duration_ms=int(v.get("duration_ms") or 0),
                             timestamp_ms=ts,
                             run_id=v.get("run_id") or self._cur_run,
                             tool_call_id=v.get("tool_call_id"),
                             mount_prefix=v.get("mount_prefix"),
                             fingerprint=v.get("fingerprint"),
                             revision=v.get("revision")))
        else:
            out.events.append(self._row(ev, self._cur_run, self._cur_step))
        return out

    def _flush_text(self, mid: str, end_ev: dict) -> list[EventRow]:
        b = self._msg.pop(mid, None)
        if b is None:
            return [self._row(end_ev, self._cur_run, self._cur_step)]
        rows = [self._row(b["start"], self._cur_run, b["step_id"])]
        if b["content"]:
            content_ev = {
                "type": "TEXT_MESSAGE_CONTENT",
                "timestamp": b["ts"],
                "message_id": mid,
                "delta": b["content"]
            }
            rows.append(self._row(content_ev, self._cur_run, b["step_id"]))
        rows.append(self._row(end_ev, self._cur_run, b["step_id"]))
        return rows

    def _flush_thinking(self, tid: str,
                        end_ev: dict) -> tuple[list[EventRow], StepRow | None]:
        b = self._think.pop(tid, None)
        if b is None:
            return [self._row(end_ev, self._cur_run, self._cur_step)], None
        sid = b["step_id"]
        rows = [self._row(b["start"], self._cur_run, sid)]
        if b["content"]:
            content_ev = {
                "type": "THINKING_CONTENT",
                "timestamp": b["ts"],
                "thinking_id": tid,
                "delta": b["content"]
            }
            rows.append(self._row(content_ev, self._cur_run, sid))
        rows.append(self._row(end_ev, self._cur_run, sid))
        step = self._steps.get(sid)
        if step is not None and b["content"]:
            step.reasoning = (step.reasoning or "") + b["content"]
        return rows, step

    def _flush_tool(self, tcid: str, end_ev: dict) -> list[EventRow]:
        b = self._tool.pop(tcid, None)
        if b is None:
            return [self._row(end_ev, self._cur_run, self._cur_step)]
        rows = [self._row(b["start"], self._cur_run, self._cur_step)]
        if b["args"]:
            args_ev = {
                "type": "TOOL_CALL_ARGS",
                "timestamp": b["ts"],
                "tool_call_id": tcid,
                "delta": b["args"]
            }
            rows.append(self._row(args_ev, self._cur_run, self._cur_step))
        rows.append(self._row(end_ev, self._cur_run, self._cur_step))
        tool = self._tools.get(tcid)
        if tool is not None:
            tool.args = b["args"]
        return rows

    def finalize(self) -> FeedOut:
        """Flush any open buffers (abnormal termination) and mark dangling runs/steps.

        Returns:
            FeedOut: Remaining consolidated events and derived rows.
        """
        out = FeedOut()
        for mid in list(self._msg):
            out.events.extend(
                self._flush_text(mid, {
                    "type": "TEXT_MESSAGE_END",
                    "timestamp": 0,
                    "message_id": mid
                }))
        for tid in list(self._think):
            rows, step = self._flush_thinking(tid, {
                "type": "THINKING_END",
                "timestamp": 0,
                "thinking_id": tid
            })
            out.events.extend(rows)
            if step is not None:
                out.steps.append(step)
        for tcid in list(self._tool):
            out.events.extend(
                self._flush_tool(tcid, {
                    "type": "TOOL_CALL_END",
                    "timestamp": 0,
                    "tool_call_id": tcid
                }))
            tool = self._tools.get(tcid)
            if tool is not None:
                out.tool_calls.append(tool)
        for run in self._runs.values():
            if run.status == "running":
                run.status = "error"
                out.runs.append(run)
        for step in self._steps.values():
            if step.status == "running":
                step.status = "error"
                out.steps.append(step)
        return out
