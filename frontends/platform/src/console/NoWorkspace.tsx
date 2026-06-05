import { useNavigate } from "react-router-dom";
import { Boxes } from "lucide-react";
import { Button } from "@/components/ui";

export function NoWorkspace({ message }: { message?: string }) {
  const navigate = useNavigate();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-xl bg-surface-2 text-text-muted">
        <Boxes size={20} />
      </span>
      <p className="text-[13px] text-text-secondary">
        {message ?? "No active workspace."}
      </p>
      <p className="max-w-[300px] text-[11px] text-text-faint">
        Pick or stand up a workspace to run an agent and watch the captured-vs-real
        boundary.
      </p>
      <Button variant="secondary" size="sm" onClick={() => navigate("/console")}>
        Go to Workspaces
      </Button>
    </div>
  );
}
