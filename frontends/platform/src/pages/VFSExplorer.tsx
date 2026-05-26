import { useCallback, useEffect, useState } from "react";
import { listSessions, vfsList, vfsFile } from "@/api/client";

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
}

const MOUNT_COLORS: Record<string, string> = {
  tickets: "bg-mount-tickets",
  slack: "bg-mount-slack",
  github: "bg-mount-github",
  pagerduty: "bg-mount-pagerduty",
  finance: "bg-mount-finance",
  datadog: "bg-mount-datadog",
  compliance: "bg-mount-compliance",
  customers: "bg-mount-customers",
};

function getMountColor(path: string): string {
  const mount = path.split("/")[1] || "";
  return MOUNT_COLORS[mount] || "bg-text-muted";
}

export default function VFSExplorer() {
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [fileLoading, setFileLoading] = useState(false);
  const [treeError, setTreeError] = useState<string | null>(null);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
  }, []);

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
      try {
        const children = await loadDirectory(sessionId, "/");
        setTree(children);
      } catch (err) {
        setTreeError(
          err instanceof Error ? err.message : "Failed to load VFS",
        );
        setTree([]);
      }
    },
    [loadDirectory],
  );

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
    async (path: string) => {
      if (!selectedSession) return;
      setSelectedFile(path);
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-4 border-b border-border px-6 py-3">
        <h1 className="text-sm font-semibold text-text-primary">
          VFS Explorer
        </h1>
        <select
          value={selectedSession || ""}
          onChange={(e) =>
            e.target.value
              ? handleSelectSession(e.target.value)
              : setSelectedSession(null)
          }
          className="rounded-md border border-border bg-surface-2 px-3 py-1.5 font-mono text-xs text-text-primary outline-none focus:border-accent"
        >
          <option value="">Select session...</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id} ({s.message_count} msgs)
            </option>
          ))}
        </select>
        {selectedFile && (
          <span className="ml-auto font-mono text-xs text-text-muted">
            {selectedFile}
          </span>
        )}
      </div>

      {!selectedSession ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="text-3xl opacity-30">&#x1F4C2;</span>
          <span className="text-sm text-text-muted">
            Select a session to browse its VFS workspace
          </span>
        </div>
      ) : treeError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="text-sm text-danger">
            VFS not available for this session
          </span>
          <span className="text-xs text-text-muted">{treeError}</span>
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <div className="w-[320px] shrink-0 overflow-y-auto border-r border-border bg-surface-1 py-2">
            <TreeView
              nodes={tree}
              selectedFile={selectedFile}
              onToggleDir={handleToggleDir}
              onSelectFile={handleSelectFile}
            />
          </div>

          <div className="flex flex-1 flex-col overflow-hidden">
            {selectedFile ? (
              <>
                <div className="flex items-center gap-2 border-b border-border px-4 py-2">
                  <span
                    className={`h-2 w-2 rounded-full ${getMountColor(selectedFile)}`}
                  />
                  <span className="font-mono text-xs text-text-primary">
                    {selectedFile}
                  </span>
                </div>
                <div className="flex-1 overflow-auto bg-surface-0 p-4">
                  {fileLoading ? (
                    <span className="animate-pulse-fade text-sm text-text-muted">
                      Loading...
                    </span>
                  ) : (
                    <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-text-secondary">
                      {tryFormatJson(fileContent)}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <span className="text-sm text-text-muted">
                  Select a file to preview its contents
                </span>
              </div>
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
  onSelectFile: (path: string) => void;
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
  onSelectFile: (path: string) => void;
}) {
  const isDir = node.type === "dir";
  const isSelected = node.path === selectedFile;

  const handleClick = () => {
    if (isDir) onToggleDir(node.path);
    else onSelectFile(node.path);
  };

  return (
    <>
      <button
        onClick={handleClick}
        className={`flex w-full items-center gap-1.5 px-2 py-1 text-left font-mono text-xs transition-colors ${
          isSelected
            ? "bg-accent-muted text-accent"
            : "text-text-secondary hover:bg-surface-3"
        }`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        {isDir ? (
          <svg
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className={`h-3 w-3 shrink-0 transition-transform ${node.expanded ? "rotate-90" : ""}`}
          >
            <path d="M6 4l4 4-4 4" />
          </svg>
        ) : (
          <span className="h-3 w-3" />
        )}
        {isDir ? (
          <FolderSvg />
        ) : (
          <FileSvg />
        )}
        <span className="truncate">{node.name}</span>
        {depth === 0 && (
          <span
            className={`ml-auto h-1.5 w-1.5 rounded-full ${getMountColor(node.path)}`}
          />
        )}
        {node.loading && (
          <span className="ml-auto animate-spin text-text-muted">&#x25E6;</span>
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

function FolderSvg() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-3.5 w-3.5 shrink-0 text-warning"
    >
      <path d="M2 4.5A1.5 1.5 0 013.5 3H6l1.5 1.5h5A1.5 1.5 0 0114 6v5.5a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 11.5z" />
    </svg>
  );
}

function FileSvg() {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-3.5 w-3.5 shrink-0 text-text-muted"
    >
      <path d="M4 2h5l4 4v8a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" />
      <path d="M9 2v4h4" />
    </svg>
  );
}

function tryFormatJson(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}
