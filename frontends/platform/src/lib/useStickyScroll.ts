import { useCallback, useEffect, useRef, useState } from "react";

const BOTTOM_THRESHOLD_PX = 80;

export function scrollChildIntoView(
  container: HTMLElement,
  child: HTMLElement,
  block: "start" | "center" | "end" = "center",
) {
  const cRect = container.getBoundingClientRect();
  const tRect = child.getBoundingClientRect();
  const relativeTop = tRect.top - cRect.top + container.scrollTop;
  let top = relativeTop;
  if (block === "center") {
    top = relativeTop - (container.clientHeight - child.offsetHeight) / 2;
  } else if (block === "end") {
    top = relativeTop - container.clientHeight + child.offsetHeight;
  }
  container.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

export function useStickyScroll(active: boolean, scrollDeps: unknown[]) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const measureAtBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    return distance < BOTTOM_THRESHOLD_PX;
  }, []);

  useEffect(() => {
    if (!active) return;
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => setAtBottom(measureAtBottom());
    onScroll();
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [active, measureAtBottom, ...scrollDeps]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    if (behavior === "auto") {
      setAtBottom(true);
    }
  }, []);

  const scrollToElement = useCallback(
    (target: HTMLElement, block: "start" | "center" | "end" = "center") => {
      const el = scrollRef.current;
      if (!el) {
        target.scrollIntoView({ behavior: "smooth", block });
        return;
      }
      scrollChildIntoView(el, target, block);
    },
    [],
  );

  useEffect(() => {
    if (!active || !atBottom) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [active, atBottom, ...scrollDeps]);

  const jumpToLatest = useCallback(() => {
    scrollToBottom("smooth");
    setAtBottom(true);
  }, [scrollToBottom]);

  return {
    scrollRef,
    endRef,
    atBottom,
    setAtBottom,
    scrollToBottom,
    scrollToElement,
    jumpToLatest,
  };
}
