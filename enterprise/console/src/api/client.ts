const BASE = "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function createSession(
  services: string[],
): Promise<{ id: string }> {
  return postJson("/sessions", { services });
}

export async function runSession(
  id: string,
  task: string,
): Promise<{ id: string; status: string }> {
  return postJson(`/sessions/${id}/run`, { task });
}

export async function getSessionStatus(id: string) {
  return fetchJson<{ id: string; status: string; task: string }>(
    `/sessions/${id}/status`,
  );
}

export async function getSessionResult(id: string) {
  return fetchJson<{
    summary: string;
    services_touched: Record<string, number>;
    files_created: Record<string, string>;
    commands_run: number;
    duration_s: number;
  }>(`/sessions/${id}/result`);
}

export async function listSessions() {
  return fetchJson<
    {
      id: string;
      status: string;
      task: string;
      created_at: number;
      completed_at: number | null;
    }[]
  >("/sessions");
}

export async function getQuickActions() {
  return fetchJson<
    { id: string; label: string; services: string[]; task: string }[]
  >("/quick-actions");
}
