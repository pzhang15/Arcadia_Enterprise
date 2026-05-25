import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SessionHistory from "../SessionHistory";

const SESSIONS = [
  { id: "s1", status: "ready", services: ["it"], created_at: Date.now() / 1000 - 120, message_count: 3, last_message: "Triaged tickets" },
  { id: "s2", status: "ready", services: ["finance"], created_at: Date.now() / 1000 - 7200, message_count: 5, last_message: "Reviewed expenses" },
];

describe("SessionHistory", () => {
  it("shows empty state", () => {
    render(
      <SessionHistory sessions={[]} activeId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("No sessions yet")).toBeInTheDocument();
  });

  it("renders sessions with message counts", () => {
    render(
      <SessionHistory sessions={SESSIONS} activeId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("Triaged tickets")).toBeInTheDocument();
    expect(screen.getByText("Reviewed expenses")).toBeInTheDocument();
    expect(screen.getByText("3 msgs")).toBeInTheDocument();
    expect(screen.getByText("5 msgs")).toBeInTheDocument();
  });

  it("calls onSelect on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <SessionHistory sessions={SESSIONS} activeId={null} onSelect={onSelect} />,
    );

    await user.click(screen.getByText("Triaged tickets"));
    expect(onSelect).toHaveBeenCalledWith("s1");
  });

  it("shows active styling", () => {
    const { container } = render(
      <SessionHistory sessions={SESSIONS} activeId="s1" onSelect={vi.fn()} />,
    );
    const entries = container.querySelectorAll("[style*='cursor: pointer']");
    const activeEntry = Array.from(entries).find((el) =>
      el.textContent?.includes("Triaged tickets"),
    )!;
    expect(activeEntry.getAttribute("style")).toContain("var(--bg-hover)");
  });
});
