import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ChevronRight,
  File,
  FileText,
  Folder,
  FolderOpen,
  FolderTree,
  HardDrive,
  Info,
} from "lucide-react";
import { listSessions, vfsList, vfsFile } from "@/api/client";
import { cn, formatBytes } from "@/lib/utils";
import { Badge, EmptyState, SectionLabel } from "@/components/ui";
import { useInvestigations } from "@/lib/investigationStore";

interface VfsEntry {
  name: string;
  type: "dir" | "file";
  size?: number;
}

interface TreeNode {
  name: string;
  path: string;
  type: "dir" | "file";
  size?: number;
  children?: TreeNode[];
  expanded?: boolean;
  loading?: boolean;
}

interface SessionEntry {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
  has_workspace?: boolean;
}

const MOUNT_COLORS: Record<string, string> = {
  tickets: "text-mount-tickets",
  slack: "text-mount-slack",
  github: "text-mount-github",
  pagerduty: "text-mount-pagerduty",
  finance: "text-mount-finance",
  datadog: "text-mount-datadog",
  compliance: "text-mount-compliance",
  customers: "text-mount-customers",
};

const MOUNT_BG_COLORS: Record<string, string> = {
  tickets: "bg-mount-tickets",
  slack: "bg-mount-slack",
  github: "bg-mount-github",
  pagerduty: "bg-mount-pagerduty",
  finance: "bg-mount-finance",
  datadog: "bg-mount-datadog",
  compliance: "bg-mount-compliance",
  customers: "bg-mount-customers",
};

function getMount(path: string): string {
  return path.split("/")[1] || "";
}

function getMountColor(path: string): string {
  return MOUNT_COLORS[getMount(path)] || "text-text-muted";
}

function getMountBg(path: string): string {
  return MOUNT_BG_COLORS[getMount(path)] || "bg-text-muted";
}

export default function VFSExplorer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const investigations = useInvestigations();

  const initialSession = searchParams.get("session");
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [selectedSession, setSelectedSession] = useState<string | null>(
    initialSession,
  );
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFileSize, setSelectedFileSize] = useState<number | undefined>();
  const [fileContent, setFileContent] = useState<string>("");
  const [fileLoading, setFileLoading] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((rows) => {
        if (cancelled) return;
        setSessions(rows);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setSessionsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const workspaceSessions = useMemo(() => {
    return sessions.filter((s) => s.has_workspace !== false);
  }, [sessions]);

  const loadDirectory = useCallback(
    async (sessionId: string, path: string): Promise<TreeNode[]> => {
      const res = await vfsList(sessionId, path);
      return res.entries.map((e: VfsEntry) => ({
        name: e.name,
        path: path === "/" ? `/${e.name}` : `${path}/${e.name}`,
        type: e.type,
        size: e.size,
        children: e.type === "dir" ? [] : undefined,
        expanded: false,
      }));
    },
    [],
  );

  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setSelectedSession(sessionId);
      setSelectedFile(null);
      setFileContent("");
      setTreeError(null);
      setTree([]);
      const params = new URLSearchParams(searchParams);
      params.set("session", sessionId);
      setSearchParams(params, { replace: true });
      try {
        const children = await loadDirectory(sessionId, "/");
        setTree(children);
      } catch (err) {
        setTreeError(
          err instanceof Error ? err.message : "Failed to load VFS",
        );
      }
    },
    [loadDirectory, searchParams, setSearchParams],
  );

  // Auto-load when bound via URL
  useEffect(() => {
    if (!initialSession) return;
    if (!sessionsLoaded) return;
    if (tree.length > 0 || treeError) return;
    handleSelectSession(initialSession);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSession, sessionsLoaded]);

  // If no session bound, default to the most recent workspace-bearing session
  useEffect(() => {
    if (selectedSession) return;
    if (!sessionsLoaded) return;
    const candidate = workspaceSessions[0];
    if (candidate) handleSelectSession(candidate.id);
  }, [selectedSession, sessionsLoaded, workspaceSessions, handleSelectSession]);

  const handleToggleDir = useCallback(
    async (path: string) => {
      if (!selectedSession) return;

      setTree((prev) => {
        const toggleNode = (nodes: TreeNode[]): TreeNode[] =>
          nodes.map((n) => {
            if (n.path === path) {
              if (n.expanded) return { ...n, expanded: false };
              return { ...n, expanded: true, loading: true };
            }
            if (n.children) return { ...n, children: toggleNode(n.children) };
            return n;
          });
        return toggleNode(prev);
      });

      try {
        const children = await loadDirectory(selectedSession, path);
        setTree((prev) => {
          const updateNode = (nodes: TreeNode[]): TreeNode[] =>
            nodes.map((n) => {
              if (n.path === path)
                return { ...n, children, expanded: true, loading: false };
              if (n.children)
                return { ...n, children: updateNode(n.children) };
              return n;
            });
          return updateNode(prev);
        });
      } catch {
        setTree((prev) => {
          const updateNode = (nodes: TreeNode[]): TreeNode[] =>
            nodes.map((n) => {
              if (n.path === path) return { ...n, loading: false };
              if (n.children)
                return { ...n, children: updateNode(n.children) };
              return n;
            });
          return updateNode(prev);
        });
      }
    },
    [selectedSession, loadDirectory],
  );

  const handleSelectFile = useCallback(
    async (path: string, size?: number) => {
      if (!selectedSession) return;
      setSelectedFile(path);
      setSelectedFileSize(size);
      setFileLoading(true);
      try {
        const res = await vfsFile(selectedSession, path);
        setFileContent(res.content);
      } catch {
        setFileContent("(Failed to load file content)");
      } finally {
        setFileLoading(false);
      }
    },
    [selectedSession],
  );

  const pathSegments = selectedFile
    ? selectedFile.split("/").filter(Boolean)
    : [];

  const currentInvestigation = selectedSession
    ? investigations[selectedSession]
    : null;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
        <div>
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Workspace Inspector
          </h1>
          <p className="text-[11px] text-text-muted">
            Browse the Mirage virtual filesystem an investigation sees
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <SectionLabel className="text-text-muted">Investigation</SectionLabel>
          <div className="relative">
            <HardDrive
              size={13}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <select
              value={selectedSession || ""}
              onChange={(e) => {
                if (e.target.value) handleSelectSession(e.target.value);
              }}
              className="h-9 min-w-[300px] rounded-lg border border-border bg-surface-2 pl-8 pr-3 font-mono text-[12px] text-text-primary focus:border-accent"
            >
              <option value="">Select an investigation…</option>
              {workspaceSessions.length > 0 && (
                <optgroup label="With workspace">
                  {workspaceSessions.map((s) => {
                    const meta = investigations[s.id];
                    return (
                      <option key={s.id} value={s.id}>
                        {meta?.title?.slice(0, 40) || s.id} · {s.id}
                      </option>
                    );
                  })}
                </optgroup>
              )}
              {sessions.length > workspaceSessions.length && (
                <optgroup label="No workspace (read-only)">
                  {sessions
                    .filter((s) => s.has_workspace === false)
                    .map((s) => (
                      <option key={s.id} value={s.id} disabled>
                        {s.id} (no workspace mounted)
                      </option>
                    ))}
                </optgroup>
              )}
            </select>
          </div>
          {currentInvestigation && (
            <button
              onClick={() => navigate(`/investigations/${selectedSession}`)}
              className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] text-text-secondary transition-colors hover:bg-surface-3 hover:text-text-primary"
            >
              Open investigation
              <ChevronRight size={12} />
            </button>
          )}
        </div>
      </header>

      {!sessionsLoaded ? (
        <div className="flex flex-1 items-center justify-center text-text-muted">
          <span className="text-[13px]">Loading sessions…</span>
        </div>
      ) : sessions.length === 0 ? (
        <EmptyState
          icon={<FolderTree size={22} />}
          title="No investigations yet"
          description="Dispatch an agent from the Inbox to spin up its first workspace, then come back here to inspect what it sees."
          size="lg"
          action={
            <button
              onClick={() => navigate("/dispatch")}
              className="rounded-md bg-accent px-3 py-1.5 text-[12px] text-white hover:bg-accent-hover"
            >
              Dispatch agent
            </button>
          }
        />
      ) : !selectedSession ? (
        <EmptyState
          icon={<FolderTree size={22} />}
          title="Pick an investigation to inspect"
          description="Choose one above to walk its mounted Mirage paths and read the files the agent is reading."
          size="lg"
        />
      ) : treeError ? (
        <EmptyState
          icon={<AlertCircle size={22} />}
          title="Workspace not available"
          description={
            treeError.includes("400")
              ? "This investigation was dispatched without an attached workspace — pick another one above."
              : treeError
          }
          size="lg"
        />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <div className="flex w-[340px] shrink-0 flex-col border-r border-border bg-surface-1/40">
            {currentInvestigation && (
              <div className="border-b border-border bg-surface-1/60 px-3 py-2.5">
                <div className="flex items-center gap-1.5">
                  <Info size={11} className="text-text-muted" />
                  <SectionLabel>Bound to investigation</SectionLabel>
                </div>
                <div className="mt-1 truncate text-[12px] font-semibold text-text-primary">
                  {currentInvestigation.title}
                </div>
              </div>
            )}
            <div className="border-b border-border px-4 py-2.5">
              <div className="flex items-center justify-between">
                <SectionLabel>Filesystem</SectionLabel>
                <span className="font-mono text-[10px] text-text-faint">
                  {tree.length} mounts
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              <TreeView
                nodes={tree}
                selectedFile={selectedFile}
                onToggleDir={handleToggleDir}
                onSelectFile={handleSelectFile}
              />
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-bg">
            {selectedFile ? (
              <>
                <div className="flex items-center gap-2 border-b border-border bg-surface-1/60 px-5 py-3 backdrop-blur-md">
                  <span
                    className={cn(
                      "h-2 w-2 shrink-0 rounded-full",
                      getMountBg(selectedFile),
                    )}
                  />
                  <div className="flex min-w-0 items-center gap-1 font-mono text-[12px]">
                    {pathSegments.map((seg, i) => (
                      <span key={i} className="flex items-center gap-1">
                        {i > 0 && (
                          <ChevronRight
                            size={11}
                            className="shrink-0 text-text-faint"
                          />
                        )}
                        <span
                          className={cn(
                            i === pathSegments.length - 1
                              ? "text-text-primary"
                              : "text-text-muted",
                          )}
                        >
                          {seg}
                        </span>
                      </span>
                    ))}
                  </div>
                  {selectedFileSize !== undefined && (
                    <Badge tone="outline" size="sm" mono className="ml-auto">
                      {formatBytes(selectedFileSize)}
                    </Badge>
                  )}
                </div>
                <div className="flex-1 overflow-auto bg-surface-0 p-5">
                  {fileLoading ? (
                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent" />
                      <span className="text-[12px]">Loading file…</span>
                    </div>
                  ) : (
                    <pre className="whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-text-secondary">
                      {tryFormatJson(fileContent)}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <EmptyState
                icon={<FileText size={22} />}
                title="Select a file"
                description="Pick a file from the tree to preview its contents. Directories with a colored dot represent top-level Mirage mounts."
                size="lg"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TreeView({
  nodes,
  selectedFile,
  onToggleDir,
  onSelectFile,
  depth = 0,
}: {
  nodes: TreeNode[];
  selectedFile: string | null;
  onToggleDir: (path: string) => void;
  onSelectFile: (path: string, size?: number) => void;
  depth?: number;
}) {
  return (
    <>
      {nodes.map((node) => (
        <TreeNodeRow
          key={node.path}
          node={node}
          depth={depth}
          selectedFile={selectedFile}
          onToggleDir={onToggleDir}
          onSelectFile={onSelectFile}
        />
      ))}
    </>
  );
}

function TreeNodeRow({
  node,
  depth,
  selectedFile,
  onToggleDir,
  onSelectFile,
}: {
  node: TreeNode;
  depth: number;
  selectedFile: string | null;
  onToggleDir: (path: string) => void;
  onSelectFile: (path: string, size?: number) => void;
}) {
  const isDir = node.type === "dir";
  const isSelected = node.path === selectedFile;

  const handleClick = () => {
    if (isDir) onToggleDir(node.path);
    else onSelectFile(node.path, node.size);
  };

  return (
    <>
      <button
        onClick={handleClick}
        className={cn(
          "group flex w-full items-center gap-1.5 px-2 py-1 text-left font-mono text-[11.5px] transition-colors",
          isSelected
            ? "bg-accent-soft text-accent"
            : "text-text-secondary hover:bg-surface-2 hover:text-text-primary",
        )}
        style={{ paddingLeft: `${8 + depth * 14}px` }}
      >
        <span className="grid h-3 w-3 shrink-0 place-items-center">
          {isDir ? (
            <ChevronRight
              size={11}
              className={cn(
                "transition-transform text-text-muted",
                node.expanded && "rotate-90",
              )}
            />
          ) : (
            <span />
          )}
        </span>
        {isDir ? (
          node.expanded ? (
            <FolderOpen
              size={13}
              className={cn(
                "shrink-0",
                depth === 0 ? getMountColor(node.path) : "text-warning",
              )}
            />
          ) : (
            <Folder
              size={13}
              className={cn(
                "shrink-0",
                depth === 0 ? getMountColor(node.path) : "text-warning",
              )}
            />
          )
        ) : (
          <File size={13} className="shrink-0 text-text-muted" />
        )}
        <span className="truncate">{node.name}</span>
        {!isDir && node.size !== undefined && (
          <span className="ml-auto text-[10px] text-text-faint">
            {formatBytes(node.size)}
          </span>
        )}
        {depth === 0 && (
          <span
            className={cn(
              "ml-auto h-1.5 w-1.5 shrink-0 rounded-full",
              getMountBg(node.path),
            )}
          />
        )}
        {node.loading && (
          <span className="ml-auto h-2.5 w-2.5 animate-spin rounded-full border-[1.5px] border-text-muted border-r-transparent" />
        )}
      </button>
      {isDir && node.expanded && node.children && (
        <TreeView
          nodes={node.children}
          depth={depth + 1}
          selectedFile={selectedFile}
          onToggleDir={onToggleDir}
          onSelectFile={onSelectFile}
        />
      )}
    </>
  );
}

function tryFormatJson(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}
