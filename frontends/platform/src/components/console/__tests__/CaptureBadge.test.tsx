import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CaptureBadge } from "../CaptureBadge";

describe("CaptureBadge", () => {
  it("renders the label for each capture state", () => {
    const { rerender } = render(<CaptureBadge state="captured" />);
    expect(screen.getByText("CAPTURED")).toBeInTheDocument();
    rerender(<CaptureBadge state="simulated" />);
    expect(screen.getByText("SIMULATED")).toBeInTheDocument();
    rerender(<CaptureBadge state="live" />);
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("uses the reserved live color and an irreversible caption", () => {
    render(<CaptureBadge state="live" />);
    const badge = screen.getByText("LIVE");
    expect(badge.className).toContain("text-live");
    expect(badge.getAttribute("title")).toMatch(/irreversible/);
  });

  it("captioned captured as reversible overlay state", () => {
    render(<CaptureBadge state="captured" />);
    expect(screen.getByText("CAPTURED").getAttribute("title")).toMatch(
      /reversible/,
    );
  });

  it("hides the label in iconOnly mode", () => {
    render(<CaptureBadge state="captured" iconOnly />);
    expect(screen.queryByText("CAPTURED")).not.toBeInTheDocument();
  });
});
