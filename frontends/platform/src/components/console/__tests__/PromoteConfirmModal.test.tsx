import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PromoteConfirmModal } from "../PromoteConfirmModal";
import type { PendingEffect } from "@/types/console";

function effect(over: Partial<PendingEffect> = {}): PendingEffect {
  return {
    key: "k1",
    op: "write",
    path: "/scratch/x",
    mount_prefix: "/scratch",
    source: "ram",
    bytes: 10,
    effect_class: "scratch",
    capture_state: "captured",
    target: "/scratch/x",
    reversibility: "",
    promoted: false,
    timestamp: 0,
    ...over,
  };
}

describe("PromoteConfirmModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <PromoteConfirmModal open={false} effects={[]} onConfirm={() => {}} onCancel={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("always discloses that the commit is simulated", () => {
    render(
      <PromoteConfirmModal open effects={[effect()]} onConfirm={() => {}} onCancel={() => {}} />,
    );
    expect(screen.getByText(/Simulated commit/)).toBeInTheDocument();
  });

  it("enables promotion immediately for non-external effects", async () => {
    const onConfirm = vi.fn();
    render(
      <PromoteConfirmModal open effects={[effect()]} onConfirm={onConfirm} onCancel={() => {}} />,
    );
    const btn = screen.getByRole("button", { name: /Promote 1/ });
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("requires a typed PROMOTE confirmation for external effects", async () => {
    const onConfirm = vi.fn();
    render(
      <PromoteConfirmModal
        open
        effects={[effect({ effect_class: "external-effect", capture_state: "simulated" })]}
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    const btn = screen.getByRole("button", { name: /Promote 1/ });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/irreversible/)).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText("PROMOTE"), "PROMOTE");
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
