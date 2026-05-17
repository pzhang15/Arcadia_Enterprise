import { useEffect, useRef, useState } from "react";
import { getQuickActions } from "../api/client";
import type { QuickAction } from "../types";

export interface ChatMessage {
  id: string;
  role: "user" | "agent" | "system";
  text: string;
  timestamp: number;
}

interface Props {
  messages: ChatMessage[];
  onSend: (task: string, quickAction?: QuickAction) => void;
  disabled: boolean;
}

export default function TaskDialog({ messages, onSend, disabled }: Props) {
  const [input, setInput] = useState("");
  const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getQuickActions()
      .then(setQuickActions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || disabled) return;
    setInput("");
    onSend(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = (action: QuickAction) => {
    if (disabled) return;
    onSend(action.task, action);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {messages.length === 0 && quickActions.length > 0 && (
        <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
          <div
            className="sidebar-section"
            style={{ padding: "0 0 8px" }}
          >
            Quick Actions
          </div>
          <div className="quick-actions">
            {quickActions.map((action) => (
              <button
                key={action.id}
                className="quick-action-btn"
                onClick={() => handleQuickAction(action)}
                disabled={disabled}
              >
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  style={{ width: 14, height: 14, flexShrink: 0 }}
                >
                  <path d="M6 3l5 5-5 5" />
                </svg>
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <div className="empty-state-icon">$</div>
            <div className="empty-state-text">
              Select services and describe a task, or pick a quick action above.
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message ${msg.role}`}>
            {msg.text}
          </div>
        ))}
        {disabled && messages.length > 0 && (
          <div className="chat-message system">
            <span className="pulse">Agent is working...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <textarea
          className="chat-input"
          rows={1}
          placeholder={disabled ? "Agent is running..." : "Describe a task for the agent..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={disabled || !input.trim()}
        >
          Run
        </button>
      </div>
    </div>
  );
}
