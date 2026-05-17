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
): Promise<{ id: string; status: string; has_workspace: boolean }> {
  return postJson("/sessions", { services });
}

export async function sendMessage(
  sessionId: string,
  message: string,
): Promise<{ reply: string; status: string }> {
  return postJson(`/sessions/${sessionId}/message`, { message });
}

export async function getSessionStatus(id: string) {
  return fetchJson<{
    id: string;
    status: string;
    message_count: number;
  }>(`/sessions/${id}/status`);
}

export async function getSessionHistory(id: string) {
  return fetchJson<
    { role: string; content: string; timestamp: number }[]
  >(`/sessions/${id}/history`);
}

export async function listSessions() {
  return fetchJson<
    {
      id: string;
      status: string;
      services: string[];
      created_at: number;
      message_count: number;
      last_message: string;
    }[]
  >("/sessions");
}

export async function getQuickActions() {
  return fetchJson<
    { id: string; label: string; services: string[]; task: string }[]
  >("/quick-actions");
}

export async function getConfig() {
  return fetchJson<{ has_api_key: boolean; model: string }>("/config");
}
