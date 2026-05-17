import { useState } from "react";
import type { AgentResult } from "../types";

interface Props {
  result: AgentResult | null;
  sessionId: string | null;
  status: string;
}

export default function ResultsSummary({ result, sessionId, status }: Props) {
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  if (!sessionId) {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <div className="empty-state-icon">&#x1F4CB;</div>
        <div className="empty-state-text">
          Results will appear here when an agent session completes.
        </div>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <div className="empty-state-icon pulse">&#x2699;</div>
        <div className="empty-state-text">Agent is running. Results will appear when complete.</div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <div className="empty-state-icon">&#x1F4CB;</div>
        <div className="empty-state-text">No results yet.</div>
      </div>
    );
  }

  const touchedEntries = Object.entries(result.services_touched).sort(
    ([, a], [, b]) => b - a,
  );
  const fileEntries = Object.entries(result.files_created);

  return (
    <div>
      <div className="results-section">
        <h3>Session Stats</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <div className="stat-card" style={{ padding: 12 }}>
            <div className="stat-label">Duration</div>
            <div className="stat-value" style={{ fontSize: 18 }}>
              {result.duration_s}s
            </div>
          </div>
          <div className="stat-card" style={{ padding: 12 }}>
            <div className="stat-label">Commands</div>
            <div className="stat-value" style={{ fontSize: 18 }}>
              {result.commands_run}
            </div>
          </div>
        </div>
      </div>

      <div className="results-section">
        <h3>Services Touched</h3>
        <div className="service-summary">
          {touchedEntries.map(([svc, count]) => (
            <span key={svc} className="badge info">
              {svc}: {count}
            </span>
          ))}
        </div>
      </div>

      {fileEntries.length > 0 && (
        <div className="results-section">
          <h3>Files Created</h3>
          {fileEntries.map(([path, content]) => (
            <div key={path} style={{ marginBottom: 8 }}>
              <button
                className="quick-action-btn"
                style={{ width: "100%", marginBottom: 4 }}
                onClick={() =>
                  setExpandedFile(expandedFile === path ? null : path)
                }
              >
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  style={{
                    width: 12,
                    height: 12,
                    flexShrink: 0,
                    transform:
                      expandedFile === path ? "rotate(90deg)" : "none",
                    transition: "transform 0.15s",
                  }}
                >
                  <path d="M6 3l5 5-5 5" />
                </svg>
                <span className="mono" style={{ fontSize: 11 }}>
                  {path}
                </span>
              </button>
              {expandedFile === path && (
                <div className="result-file">{content}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="results-section">
        <h3>Agent Report</h3>
        <div className="result-file">{result.summary}</div>
      </div>
    </div>
  );
}
