import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ServiceConnector from "../ServiceConnector";

const ALL_SERVICES = [
  "IT Services",
  "HR & People",
  "Finance",
  "Engineering",
  "Customer Support",
  "Compliance",
];

function setup(selected = new Set<string>()) {
  const onToggle = vi.fn();
  const result = render(
    <ServiceConnector selected={selected} onToggle={onToggle} />,
  );
  return { ...result, onToggle };
}

describe("ServiceConnector", () => {
  it("renders all 6 services", () => {
    setup();
    for (const name of ALL_SERVICES) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
  });

  it("shows active state for selected services", () => {
    setup(new Set(["it", "finance"]));
    const itBtn = screen.getByText("IT Services").closest("button")!;
    const finBtn = screen.getByText("Finance").closest("button")!;
    const hrBtn = screen.getByText("HR & People").closest("button")!;

    expect(itBtn.className).toContain("active");
    expect(finBtn.className).toContain("active");
    expect(hrBtn.className).not.toContain("active");
  });

  it("calls onToggle on click", async () => {
    const user = userEvent.setup();
    const { onToggle } = setup();

    await user.click(screen.getByText("Engineering").closest("button")!);
    expect(onToggle).toHaveBeenCalledWith("engineering");
  });

  it("shows connected count", () => {
    setup(new Set(["it", "hr", "finance"]));
    expect(screen.getByText("3 of 6 connected")).toBeInTheDocument();
  });
});
