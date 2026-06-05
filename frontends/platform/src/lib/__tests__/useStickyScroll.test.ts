import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { scrollChildIntoView } from "../useStickyScroll";

describe("scrollChildIntoView", () => {
  it("calls scrollTo on the scroll container", () => {
    const container = document.createElement("div");
    const child = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 200 });
    container.appendChild(child);
    document.body.appendChild(container);

    container.getBoundingClientRect = () =>
      ({
        top: 0,
        left: 0,
        height: 200,
        width: 100,
      }) as DOMRect;
    child.getBoundingClientRect = () =>
      ({
        top: 400,
        left: 0,
        height: 40,
        width: 100,
      }) as DOMRect;
    Object.defineProperty(child, "offsetHeight", { value: 40 });

    const scrollTo = vi.spyOn(container, "scrollTo");
    scrollChildIntoView(container, child, "center");
    expect(scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: "smooth" }),
    );

    document.body.removeChild(container);
  });
});

describe("useStickyScroll", () => {
  it("exports jump helper via hook", async () => {
    const { useStickyScroll } = await import("../useStickyScroll");
    const { result } = renderHook(() => useStickyScroll(true, [0]));
    expect(result.current.scrollRef).toBeDefined();
    expect(result.current.jumpToLatest).toBeTypeOf("function");
  });
});
