import { GitBranch, GitFork } from "lucide-react";
import type { ConsoleWorkspaceBrief } from "@/types/console";
import { cn } from "@/lib/utils";

interface TreeNode {
  ws: ConsoleWorkspaceBrief;
  children: TreeNode[];
}

function buildForest(workspaces: ConsoleWorkspaceBrief[]): TreeNode[] {
  const byId = new Map<string, TreeNode>();
  for (const ws of workspaces) byId.set(ws.id, { ws, children: [] });
  const roots: TreeNode[] = [];
  for (const node of byId.values()) {
    const parentId = node.ws.parent_id;
    const parent = parentId ? byId.get(parentId) : null;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  return roots.sort((a, b) => a.ws.created_at - b.ws.created_at);
}

interface Props {
  workspaces: ConsoleWorkspaceBrief[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

export function BranchTree({ workspaces, activeId, onSelect }: Props) {
  const forest = buildForest(workspaces);
  return (
    <div className="flex flex-col gap-0.5">
      {forest.map((node) => (
        <BranchNode
          key={node.ws.id}
          node={node}
          depth={0}
          activeId={activeId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

function BranchNode({
  node,
  depth,
  activeId,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  const { ws } = node;
  const isActive = ws.id === activeId;
  const isRoot = depth === 0;
  return (
    <>
      <button
        onClick={() => onSelect(ws.id)}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        className={cn(
          "group flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-left transition-colors",
          isActive ? "bg-accent-soft" : "hover:bg-surface-2",
        )}
      >
        {isRoot ? (
          <GitBranch size={13} className="shrink-0 text-text-muted" />
        ) : (
          <GitFork size={13} className="shrink-0 text-text-faint" />
        )}
        <span
          className={cn(
            "truncate text-[12px]",
            isActive ? "font-medium text-accent" : "text-text-secondary",
          )}
        >
          {ws.branch}
        </span>
        {ws.pending_effects > 0 && (
          <span className="ml-auto shrink-0 rounded-full bg-simulated-soft px-1.5 font-mono text-[9px] text-simulated tabular-nums">
            {ws.pending_effects}
          </span>
        )}
        <span
          className={cn(
            "shrink-0 rounded-full px-1.5 font-mono text-[9px] uppercase",
            ws.mode === "LIVE"
              ? "bg-live-soft text-live"
              : "bg-surface-3 text-text-muted",
            ws.pending_effects > 0 ? "" : "ml-auto",
          )}
        >
          {ws.mode}
        </span>
      </button>
      {node.children
        .sort((a, b) => a.ws.created_at - b.ws.created_at)
        .map((child) => (
          <BranchNode
            key={child.ws.id}
            node={child}
            depth={depth + 1}
            activeId={activeId}
            onSelect={onSelect}
          />
        ))}
    </>
  );
}
