import { Route, Routes } from "react-router-dom";
import { Boxes } from "lucide-react";
import { selectActiveDetail, useConsoleStore } from "@/lib/consoleStore";
import RunHistoryV3 from "./RunHistoryV3";
import RunDebuggerV3 from "./RunDebuggerV3";

export default function ConsoleV3() {
  const ws = selectActiveDetail(useConsoleStore());
  return (
    <div className="flex h-screen min-w-[980px] flex-col overflow-hidden text-text-primary">
      <header className="flex h-11 shrink-0 items-center gap-3 border-b border-border bg-surface-1/80 px-3 backdrop-blur-xl">
        <div className="grid h-6 w-6 place-items-center rounded-md bg-gradient-to-br from-accent to-info text-white">
          <Boxes size={14} />
        </div>
        <span className="text-[13px] font-semibold tracking-tight">
          Mirage Console
        </span>
        <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-[10px] text-text-muted">
          v3 · runs
        </span>
        {ws && (
          <span className="font-mono text-[11px] text-text-muted">
            · {ws.name} · {ws.branch}
          </span>
        )}
        <span className="ml-auto rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-text-muted">
          Search &amp; jump&nbsp;&nbsp;⌘K
        </span>
      </header>
      <main className="min-h-0 flex-1">
        <Routes>
          <Route index element={<RunHistoryV3 />} />
          <Route path="runs/:sessionId" element={<RunDebuggerV3 />} />
        </Routes>
      </main>
    </div>
  );
}
