import { useCallback, useSyncExternalStore } from "react";

export type ChatViewMode = "tui" | "im";

const STORAGE_KEY = "hermes-chat-view-mode";

function getSnapshot(): ChatViewMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "im" || stored === "tui") return stored;
  } catch {}
  return "tui";
}

function getServerSnapshot(): ChatViewMode {
  return "tui";
}

const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function setMode(mode: ChatViewMode) {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {}
  for (const cb of listeners) cb();
}

export function useChatViewMode() {
  const mode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = useCallback(() => {
    setMode(mode === "tui" ? "im" : "tui");
  }, [mode]);

  const set = useCallback((m: ChatViewMode) => {
    setMode(m);
  }, []);

  return { mode, toggle, setMode: set };
}
