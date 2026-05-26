interface Props {
  sessionId: string | null;
  eventCount: number;
  connected: boolean;
}

export default function ResultsSummary({
  sessionId,
  eventCount,
  connected,
}: Props) {
  if (!sessionId) {
    return (
      <div className="empty-state" style={{ padding: "40px 16px" }}>
        <div className="empty-state-icon" style={{ fontSize: 28 }}>
          &gt;_
        </div>
        <div className="empty-state-text">
          Start a conversation to see live activity here. Commands the agent
          runs will appear in the execution view.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 16 }}>
      <div className="results-section">
        <h3>Session</h3>
        <div className="stat-card" style={{ marginBottom: 12 }}>
          <div className="stat-label">Session ID</div>
          <div className="mono" style={{ fontSize: 13 }}>
            {sessionId}
          </div>
        </div>
      </div>

      <div className="results-section">
        <h3>Stream</h3>
        <div className="flex items-center gap-2" style={{ marginBottom: 8 }}>
          <div
            className={`connection-dot ${connected ? "connected" : ""}`}
          />
          <span className="text-sm">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="stat-card">
          <div className="stat-label">Events Captured</div>
          <div className="stat-value">{eventCount}</div>
        </div>
      </div>
    </div>
  );
}
