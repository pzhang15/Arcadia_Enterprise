import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatBytes(b: number): string {
  if (b < 1024) return `${b}B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}KB`;
  return `${(b / (1024 * 1024)).toFixed(1)}MB`;
}

export function timeAgo(ts: number): string {
  const diff = (Date.now() / 1000 - ts) | 0;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${(diff / 60) | 0}m ago`;
  if (diff < 86400) return `${(diff / 3600) | 0}h ago`;
  return `${(diff / 86400) | 0}d ago`;
}
