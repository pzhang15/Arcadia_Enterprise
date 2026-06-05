import { useEffect, useState } from "react";
import {
  deleteInvestigationApi,
  listInvestigations,
  upsertInvestigationApi,
} from "@/api/client";
import type {
  InvestigationAuthority,
  InvestigationMeta,
  InvestigationSeverity,
  InvestigationStatus,
  InvestigationTrigger,
} from "@/types/investigation";

const STORAGE_KEY = "arcadia.investigations.v1";

type Listener = () => void;
const listeners = new Set<Listener>();

function safeRead(): Record<string, InvestigationMeta> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    return parsed as Record<string, InvestigationMeta>;
  } catch {
    return {};
  }
}

function safeWrite(data: Record<string, InvestigationMeta>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore quota / serialization errors
  }
}

function emit() {
  for (const l of listeners) l();
}

function writeOne(meta: InvestigationMeta) {
  const all = safeRead();
  all[meta.sessionId] = meta;
  safeWrite(all);
  emit();
}

export function getAllInvestigations(): Record<string, InvestigationMeta> {
  return safeRead();
}

export function getInvestigation(sessionId: string): InvestigationMeta | null {
  return safeRead()[sessionId] || null;
}

export interface UpsertInput {
  sessionId: string;
  title?: string;
  templateId?: string;
  severity?: InvestigationSeverity;
  status?: InvestigationStatus;
  trigger?: InvestigationTrigger;
  triggerRef?: string;
  authority?: InvestigationAuthority;
  brief?: string;
  resolution?: string;
  resolvedAt?: number;
  escalatedTo?: string;
}

export function upsertInvestigation(input: UpsertInput): InvestigationMeta {
  const all = safeRead();
  const now = Date.now();
  const existing = all[input.sessionId];
  const next: InvestigationMeta = {
    sessionId: input.sessionId,
    title: input.title ?? existing?.title ?? "Untitled investigation",
    templateId: input.templateId ?? existing?.templateId ?? "custom",
    severity: input.severity ?? existing?.severity ?? "P3",
    status: input.status ?? existing?.status ?? "running",
    trigger: input.trigger ?? existing?.trigger ?? "manual",
    triggerRef: input.triggerRef ?? existing?.triggerRef,
    authority: input.authority ?? existing?.authority ?? "read_only",
    brief: input.brief ?? existing?.brief,
    resolution: input.resolution ?? existing?.resolution,
    resolvedAt: input.resolvedAt ?? existing?.resolvedAt,
    escalatedTo: input.escalatedTo ?? existing?.escalatedTo,
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
  };
  // Optimistic local write, then reconcile with the server.
  writeOne(next);
  upsertInvestigationApi(next)
    .then((server) => writeOne(server))
    .catch((err) => console.warn("investigation sync failed", err));
  return next;
}

export function setInvestigationStatus(
  sessionId: string,
  status: InvestigationStatus,
  extras: Partial<UpsertInput> = {},
): InvestigationMeta | null {
  const existing = getInvestigation(sessionId);
  if (!existing) return null;
  return upsertInvestigation({ sessionId, status, ...extras });
}

export function deleteInvestigation(sessionId: string) {
  const all = safeRead();
  if (!(sessionId in all)) return;
  delete all[sessionId];
  safeWrite(all);
  emit();
  deleteInvestigationApi(sessionId).catch((err) =>
    console.warn("investigation delete failed", err),
  );
}

export function resetInvestigations() {
  safeWrite({});
  emit();
}

export async function hydrateInvestigations(): Promise<void> {
  try {
    const rows = await listInvestigations();
    const map: Record<string, InvestigationMeta> = {};
    for (const meta of rows) map[meta.sessionId] = meta;
    safeWrite(map);
    emit();
  } catch (err) {
    console.warn("investigation hydrate failed", err);
  }
}

function subscribe(l: Listener) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

export function useInvestigations(): Record<string, InvestigationMeta> {
  const [snapshot, setSnapshot] = useState<Record<string, InvestigationMeta>>(
    () => safeRead(),
  );
  useEffect(() => subscribe(() => setSnapshot(safeRead())), []);
  return snapshot;
}

export function useInvestigation(
  sessionId: string | null | undefined,
): InvestigationMeta | null {
  const all = useInvestigations();
  if (!sessionId) return null;
  return all[sessionId] || null;
}
