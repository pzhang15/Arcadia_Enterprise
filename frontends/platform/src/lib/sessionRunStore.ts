import { getSessionHistory, getSessionTrace } from "@/api/client";
import {
  applyAguiEvent,
  createReducerRefs,
  INITIAL_AGENT_STREAM_STATE,
  messagesFromChatHistory,
  replayAguiEvents,
  type AgentStreamState,
  type ReducerRefs,
} from "@/lib/aguiEventReducer";
import type { AGUIEvent, MessageBlock } from "@/types/agui";

const STORAGE_KEY = "arcadia.session-run.v1";
const PERSIST_DEBOUNCE_MS = 400;

type Listener = () => void;

const states = new Map<string, AgentStreamState>();
const listeners = new Map<string, Set<Listener>>();
const abortControllers = new Map<string, AbortController>();
const hydrated = new Set<string>();
const hydrateInflight = new Map<string, Promise<void>>();
const persistTimers = new Map<string, ReturnType<typeof setTimeout>>();
const reducerRefsBySession = new Map<string, ReducerRefs>();

function notify(sessionId: string) {
  const set = listeners.get(sessionId);
  if (!set) return;
  for (const fn of set) {
    fn();
  }
}

function loadAllFromStorage(): Record<string, AgentStreamState> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, AgentStreamState>;
  } catch {
    return {};
  }
}

function persistToStorage(sessionId: string, state: AgentStreamState) {
  try {
    const all = loadAllFromStorage();
    all[sessionId] = state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch {
    /* quota or private mode */
  }
}

function schedulePersist(sessionId: string) {
  const existing = persistTimers.get(sessionId);
  if (existing) clearTimeout(existing);
  persistTimers.set(
    sessionId,
    setTimeout(() => {
      persistTimers.delete(sessionId);
      const state = states.get(sessionId);
      if (state) persistToStorage(sessionId, state);
    }, PERSIST_DEBOUNCE_MS),
  );
}

export function getSessionRunSnapshot(sessionId: string): AgentStreamState {
  return states.get(sessionId) ?? INITIAL_AGENT_STREAM_STATE;
}

export function subscribeSessionRun(
  sessionId: string,
  listener: Listener,
): () => void {
  let set = listeners.get(sessionId);
  if (!set) {
    set = new Set();
    listeners.set(sessionId, set);
  }
  set.add(listener);
  return () => {
    set?.delete(listener);
  };
}

export function replaceSessionRunState(
  sessionId: string,
  state: AgentStreamState,
) {
  states.set(sessionId, state);
  schedulePersist(sessionId);
  notify(sessionId);
}

export function patchSessionRunState(
  sessionId: string,
  patch: Partial<AgentStreamState>,
) {
  const prev = getSessionRunSnapshot(sessionId);
  replaceSessionRunState(sessionId, { ...prev, ...patch });
}

function reducerRefsFor(sessionId: string): ReducerRefs {
  let refs = reducerRefsBySession.get(sessionId);
  if (!refs) {
    refs = createReducerRefs();
    reducerRefsBySession.set(sessionId, refs);
  }
  return refs;
}

export function beginSessionStream(sessionId: string) {
  reducerRefsBySession.set(sessionId, createReducerRefs());
}

export function applySessionRunEvent(sessionId: string, event: AGUIEvent) {
  const prev = getSessionRunSnapshot(sessionId);
  const next = applyAguiEvent(prev, event, reducerRefsFor(sessionId));
  replaceSessionRunState(sessionId, next);
}

export function setSessionRunMessages(
  sessionId: string,
  messages: MessageBlock[],
) {
  patchSessionRunState(sessionId, { messages });
}

export function getSessionAbortController(sessionId: string): AbortController {
  let controller = abortControllers.get(sessionId);
  if (!controller) {
    controller = new AbortController();
    abortControllers.set(sessionId, controller);
  }
  return controller;
}

export function resetSessionAbortController(sessionId: string) {
  abortControllers.get(sessionId)?.abort();
  const controller = new AbortController();
  abortControllers.set(sessionId, controller);
  beginSessionStream(sessionId);
  return controller;
}

export function clearSessionRun(sessionId: string) {
  abortControllers.get(sessionId)?.abort();
  abortControllers.delete(sessionId);
  reducerRefsBySession.delete(sessionId);
  states.delete(sessionId);
  hydrated.delete(sessionId);
  const inflight = hydrateInflight.get(sessionId);
  if (inflight) {
    hydrateInflight.delete(sessionId);
  }
  try {
    const all = loadAllFromStorage();
    delete all[sessionId];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
  notify(sessionId);
}

function loadFromLocalStorage(sessionId: string): boolean {
  const all = loadAllFromStorage();
  const saved = all[sessionId];
  if (!saved || saved.messages.length === 0) return false;
  states.set(sessionId, { ...saved, isStreaming: false });
  return true;
}

export async function hydrateSessionRun(sessionId: string): Promise<void> {
  if (hydrated.has(sessionId)) return;
  const inflight = hydrateInflight.get(sessionId);
  if (inflight) return inflight;

  const promise = (async () => {
    loadFromLocalStorage(sessionId);

    if (getSessionRunSnapshot(sessionId).isStreaming) {
      hydrated.add(sessionId);
      return;
    }

    let apiEvents: AGUIEvent[] = [];
    try {
      const trace = await getSessionTrace(sessionId);
      apiEvents = trace.events;
    } catch {
      apiEvents = [];
    }

    if (getSessionRunSnapshot(sessionId).isStreaming) {
      hydrated.add(sessionId);
      return;
    }

    const current = getSessionRunSnapshot(sessionId);

    if (apiEvents.length > 0) {
      const replayed = replayAguiEvents(apiEvents);
      const shouldReplace =
        replayed.runOrder.length > current.runOrder.length ||
        (replayed.runOrder.length === current.runOrder.length &&
          replayed.messages.length > current.messages.length);
      if (shouldReplace || current.messages.length === 0) {
        replaceSessionRunState(sessionId, replayed);
      }
    } else if (current.messages.length === 0) {
      try {
        const history = await getSessionHistory(sessionId);
        if (history.length > 0) {
          setSessionRunMessages(
            sessionId,
            messagesFromChatHistory(sessionId, history),
          );
        }
      } catch {
        /* session may not exist yet */
      }
    }

    hydrated.add(sessionId);
  })();

  hydrateInflight.set(sessionId, promise);
  try {
    await promise;
  } finally {
    hydrateInflight.delete(sessionId);
  }
  notify(sessionId);
}

export function invalidateSessionHydration(sessionId: string) {
  hydrated.delete(sessionId);
}
