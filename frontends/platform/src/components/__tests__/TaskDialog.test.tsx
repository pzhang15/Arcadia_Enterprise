import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { server } from "../../test/mocks/server";
import { http, HttpResponse } from "msw";
import TaskDialog from "../TaskDialog";
import type { ChatMessage } from "../TaskDialog";

const QUICK_ACTIONS = [
  { id: "triage", label: "Triage IT helpdesk queue", services: ["it", "hr"], task: "Triage all open IT tickets." },
  { id: "expenses", label: "Review pending expenses", services: ["finance"], task: "Review all pending expense reports." },
];

function setup(props: Partial<React.ComponentProps<typeof TaskDialog>> = {}) {
  const defaultProps = {
    messages: [] as ChatMessage[],
    onSend: vi.fn(),
    disabled: false,
    ...props,
  };
  return { ...render(<TaskDialog {...defaultProps} />), props: defaultProps };
}

describe("TaskDialog", () => {
  it("renders quick actions when no messages", async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText("Triage IT helpdesk queue")).toBeInTheDocument();
      expect(screen.getByText("Review pending expenses")).toBeInTheDocument();
    });
  });

  it("hides quick actions when messages exist", async () => {
    const messages: ChatMessage[] = [
      { id: "1", role: "user", text: "hello", timestamp: Date.now() },
    ];
    setup({ messages });
    await waitFor(() => {
      expect(screen.queryByText("Triage IT helpdesk queue")).not.toBeInTheDocument();
    });
  });

  it("sends message on button click", async () => {
    const user = userEvent.setup();
    const { props } = setup();

    const textarea = screen.getByPlaceholderText(/Describe a task/);
    await user.type(textarea, "Show open tickets");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(props.onSend).toHaveBeenCalledWith("Show open tickets");
  });

  it("sends message on Enter key", async () => {
    const user = userEvent.setup();
    const { props } = setup();

    const textarea = screen.getByPlaceholderText(/Describe a task/);
    await user.type(textarea, "List expenses{enter}");

    expect(props.onSend).toHaveBeenCalledWith("List expenses");
  });

  it("disables send when processing", () => {
    setup({ disabled: true });
    const sendBtn = screen.getByRole("button", { name: "Send" });
    expect(sendBtn).toBeDisabled();
  });

  it("shows thinking indicator when disabled with messages", () => {
    const messages: ChatMessage[] = [
      { id: "1", role: "user", text: "Do something", timestamp: Date.now() },
    ];
    setup({ disabled: true, messages });
    expect(screen.getByText(/Agent is thinking/)).toBeInTheDocument();
  });

  it("clicking quick action calls onSend with action.task and action", async () => {
    const user = userEvent.setup();
    const { props } = setup();

    await waitFor(() => {
      expect(screen.getByText("Triage IT helpdesk queue")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Triage IT helpdesk queue"));

    expect(props.onSend).toHaveBeenCalledWith(
      "Triage all open IT tickets.",
      QUICK_ACTIONS[0],
    );
  });
});
