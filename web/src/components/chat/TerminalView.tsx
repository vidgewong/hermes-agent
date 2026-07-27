/**
 * TerminalView — embeds `hermes --tui` xterm.js terminal inside the dashboard.
 * Extracted from ChatPage to allow alternate view modes.
 */

import { FitAddon } from "@xterm/addon-fit";
import { Unicode11Addon } from "@xterm/addon-unicode11";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { WebglAddon } from "@xterm/addon-webgl";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { Button } from "@nous-research/ui/ui/components/button";
import { cn } from "@/lib/utils";
import { Copy, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "@/lib/api";
import { useTheme } from "@/themes";

const DEFAULT_TERMINAL_BACKGROUND = "#000000";
const DEFAULT_TERMINAL_FOREGROUND = "#f0e6d2";

function buildTerminalTheme(background: string, foreground: string) {
  return {
    background,
    foreground,
    cursor: foreground,
    cursorAccent: background,
    selectionBackground:
      foreground.length === 7 ? `${foreground}44` : foreground,
  };
}

function terminalTierWidthPx(host: HTMLElement | null): number {
  if (typeof window === "undefined") return 1280;
  const fromHost = host?.clientWidth ?? 0;
  if (fromHost > 2) return Math.round(fromHost);
  const doc = document.documentElement?.clientWidth ?? 0;
  const vv = window.visualViewport;
  const inner = window.innerWidth;
  const vvw = vv?.width ?? inner;
  const layout = Math.min(inner, vvw, doc > 0 ? doc : inner);
  return Math.max(1, Math.round(layout));
}

function terminalFontSizeForWidth(layoutWidthPx: number): number {
  if (layoutWidthPx < 300) return 7;
  if (layoutWidthPx < 360) return 8;
  if (layoutWidthPx < 420) return 9;
  if (layoutWidthPx < 520) return 10;
  if (layoutWidthPx < 720) return 11;
  if (layoutWidthPx < 1024) return 12;
  return 14;
}

function terminalLineHeightForWidth(layoutWidthPx: number): number {
  return layoutWidthPx < 1024 ? 1.02 : 1.15;
}

interface TerminalViewProps {
  isActive: boolean;
  channel: string;
  resumeParam: string | null;
  commandParam: string | null;
  scopedProfile: string;
  reconnectNonce: number;
  onReconnectNonceChange: () => void;
  onSessionEnd: () => void;
  onBannerChange: (banner: string | null) => void;
  onSessionTitleChange: (title: string | null) => void;
}

export function TerminalView({
  isActive,
  channel,
  resumeParam,
  commandParam,
  scopedProfile,
  reconnectNonce,
  onReconnectNonceChange,
  onSessionEnd,
  onBannerChange,
  onSessionTitleChange,
}: TerminalViewProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const syncMetricsRef = useRef<(() => void) | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [sessionEnded, setSessionEnded] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");
  const copyResetRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const forceFreshPtyRef = useRef(false);

  const { theme } = useTheme();
  const terminalBg = theme.terminalBackground ?? DEFAULT_TERMINAL_BACKGROUND;
  const terminalFg = theme.terminalForeground ?? DEFAULT_TERMINAL_FOREGROUND;
  const terminalTheme = useMemo(
    () => buildTerminalTheme(terminalBg, terminalFg),
    [terminalBg, terminalFg],
  );

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const reconnect = useCallback(() => {
    forceFreshPtyRef.current = true;
    reconnectAttemptRef.current = 0;
    clearReconnectTimer();
    setSessionEnded(false);
    onBannerChange(null);
    onReconnectNonceChange();
  }, [clearReconnectTimer, onBannerChange, onReconnectNonceChange]);

  const handleCopyLast = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send("/copy");
    setTimeout(() => {
      const s = wsRef.current;
      if (s && s.readyState === WebSocket.OPEN) s.send("\r");
    }, 100);
    setCopyState("copied");
    if (copyResetRef.current) clearTimeout(copyResetRef.current);
    copyResetRef.current = setTimeout(() => setCopyState("idle"), 1500);
    termRef.current?.focus();
  };

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const token = window.__HERMES_SESSION_TOKEN__;
    const gated = !!window.__HERMES_AUTH_REQUIRED__;
    if (!token && !gated) return;

    const tierW0 = terminalTierWidthPx(host);
    const term = new Terminal({
      allowProposedApi: true,
      cursorBlink: true,
      fontFamily:
        "'JetBrains Mono', 'Cascadia Mono', 'Fira Code', 'MesloLGS NF', 'Source Code Pro', Menlo, Consolas, 'DejaVu Sans Mono', monospace",
      fontSize: terminalFontSizeForWidth(tierW0),
      lineHeight: terminalLineHeightForWidth(tierW0),
      letterSpacing: 0,
      fontWeight: "400",
      fontWeightBold: "700",
      macOptionIsMeta: true,
      macOptionClickForcesSelection: true,
      rightClickSelectsWord: true,
      scrollback: 5000,
      theme: terminalTheme,
    });
    termRef.current = term;

    term.parser.registerOscHandler(52, (data) => {
      const semi = data.indexOf(";");
      if (semi < 0) return false;
      const payload = data.slice(semi + 1);
      if (payload === "?" || payload === "") return false;
      try {
        const binary = atob(payload);
        const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
        const text = new TextDecoder("utf-8").decode(bytes);
        navigator.clipboard.writeText(text).catch(() => {});
      } catch {}
      return true;
    });

    const isMac =
      typeof navigator !== "undefined" && /Mac/i.test(navigator.platform);

    term.attachCustomKeyEventHandler((ev) => {
      if (ev.type !== "keydown") return true;
      const copyModifier = isMac ? ev.metaKey : ev.ctrlKey && ev.shiftKey;
      const pasteModifier = isMac ? ev.metaKey : ev.ctrlKey && ev.shiftKey;

      if (copyModifier && ev.key.toLowerCase() === "c") {
        const sel = term.getSelection();
        if (sel) {
          navigator.clipboard.writeText(sel).catch(() => {});
          term.clearSelection();
          ev.preventDefault();
          return false;
        }
      }

      if (pasteModifier && ev.key.toLowerCase() === "v") {
        navigator.clipboard
          .readText()
          .then((text) => {
            if (text) term.paste(text);
          })
          .catch(() => {});
        ev.preventDefault();
        return false;
      }

      return true;
    });

    const fit = new FitAddon();
    fitRef.current = fit;
    term.loadAddon(fit);

    term.attachCustomWheelEventHandler((ev) => {
      const delta = ev.deltaY;
      if (!delta) return false;
      const step = Math.max(1, Math.round(Math.abs(delta) / 50));
      term.scrollLines(delta > 0 ? step : -step);
      ev.preventDefault();
      ev.stopPropagation();
      return false;
    });

    const unicode11 = new Unicode11Addon();
    term.loadAddon(unicode11);
    term.unicode.activeVersion = "11";
    term.loadAddon(new WebLinksAddon());
    term.open(host);

    const useWebgl = terminalTierWidthPx(host) >= 768;
    if (useWebgl) {
      try {
        const webgl = new WebglAddon();
        webgl.onContextLoss(() => webgl.dispose());
        term.loadAddon(webgl);
      } catch {}
    }

    let hostSyncRaf = 0;
    const scheduleHostSync = () => {
      if (hostSyncRaf) return;
      hostSyncRaf = requestAnimationFrame(() => {
        hostSyncRaf = 0;
        syncTerminalMetrics();
      });
    };

    let metricsDebounce: ReturnType<typeof setTimeout> | null = null;
    const syncTerminalMetrics = () => {
      if (!host.isConnected || host.clientWidth <= 0 || host.clientHeight <= 0) return;
      const w = terminalTierWidthPx(host);
      const nextSize = terminalFontSizeForWidth(w);
      const nextLh = terminalLineHeightForWidth(w);
      const fontChanged =
        term.options.fontSize !== nextSize || term.options.lineHeight !== nextLh;
      if (fontChanged) {
        term.options.fontSize = nextSize;
        term.options.lineHeight = nextLh;
      }
      try {
        fit.fit();
      } catch {
        return;
      }
      if (fontChanged && term.rows > 0) {
        try {
          term.refresh(0, term.rows - 1);
        } catch {}
      }
      if (fontChanged && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(`\x1b[RESIZE:${term.cols};${term.rows}]`);
      }
    };
    syncMetricsRef.current = syncTerminalMetrics;

    const scheduleSyncTerminalMetrics = () => {
      if (metricsDebounce) clearTimeout(metricsDebounce);
      metricsDebounce = setTimeout(() => {
        metricsDebounce = null;
        syncTerminalMetrics();
      }, 60);
    };

    const ro = new ResizeObserver(() => scheduleHostSync());
    ro.observe(host);
    window.addEventListener("resize", scheduleSyncTerminalMetrics);
    window.visualViewport?.addEventListener("resize", scheduleSyncTerminalMetrics);
    scheduleHostSync();
    requestAnimationFrame(() => scheduleHostSync());

    let settleRaf1 = 0;
    let settleRaf2 = 0;
    settleRaf1 = requestAnimationFrame(() => {
      settleRaf1 = 0;
      settleRaf2 = requestAnimationFrame(() => {
        settleRaf2 = 0;
        syncTerminalMetrics();
      });
    });

    let unmounting = false;
    let onDataDisposable: { dispose(): void } | null = null;
    let onResizeDisposable: { dispose(): void } | null = null;
    const forceFresh = forceFreshPtyRef.current;
    forceFreshPtyRef.current = false;

    const scheduleReconnect = (code: number) => {
      if (reconnectTimerRef.current) return;
      const attempt = Math.min(reconnectAttemptRef.current + 1, 5);
      reconnectAttemptRef.current = attempt;
      const delayMs = Math.min(250 * 2 ** (attempt - 1), 3000);
      setSessionEnded(false);
      onBannerChange(`Chat connection interrupted (code ${code}). Reconnecting…`);
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        onReconnectNonceChange();
      }, delayMs);
    };

    void (async () => {
      if (unmounting) return;
      const params: Record<string, string> = { channel };
      if (resumeParam) params.resume = resumeParam;
      if (forceFresh) params.fresh = "1";
      if (scopedProfile) params.profile = scopedProfile;
      const url = await api.buildWsUrl("/api/pty", params);
      const ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        clearReconnectTimer();
        reconnectAttemptRef.current = 0;
        onBannerChange(null);
        setSessionEnded(false);
        ws.send(`\x1b[RESIZE:${term.cols};${term.rows}]`);

        const learnSeed = searchParams.get("learn");
        if (learnSeed) {
          const next = new URLSearchParams(searchParams);
          next.delete("learn");
          setSearchParams(next, { replace: true });
          const cmd = `/learn ${learnSeed}`.trim();
          setTimeout(() => {
            try {
              wsRef.current?.send(cmd + "\r");
            } catch {}
          }, 800);
        }

        if (commandParam) {
          setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(commandParam);
            }
          }, 500);
        }
      };

      ws.onmessage = (ev) => {
        if (typeof ev.data === "string") {
          term.write(ev.data);
        } else {
          term.write(new Uint8Array(ev.data as ArrayBuffer));
        }
      };

      ws.onclose = (ev) => {
        wsRef.current = null;
        if (unmounting) return;
        if (ev.code === 4401) {
          onBannerChange(
            ev.reason
              ? `Auth failed (${ev.reason}). Reload to refresh the session.`
              : "Auth failed. Reload the page to refresh the session token.",
          );
          return;
        }
        if (ev.code === 4403) {
          onBannerChange(ev.reason ? `Refused: ${ev.reason}.` : "Refused: request host/origin doesn't match the dashboard.");
          return;
        }
        if (ev.code === 4404) {
          onBannerChange(ev.reason ? `Chat websocket unavailable: ${ev.reason}.` : "Chat websocket unavailable on this server.");
          return;
        }
        if (ev.code === 4408) {
          onBannerChange(ev.reason ? `Refused: ${ev.reason}.` : "Refused: your client isn't permitted (server bound to localhost only).");
          return;
        }
        if (ev.code === 1011) return;
        if (!ev.wasClean || ev.code === 1001 || ev.code === 1006) {
          scheduleReconnect(ev.code);
          return;
        }
        term.write(`\r\n\x1b[90m[session ended (code ${ev.code})]\x1b[0m\r\n`);
        setSessionEnded(true);
        onSessionEnd();
      };

      // eslint-disable-next-line no-control-regex
      const SGR_MOUSE_RE = /^\x1b\[<(\d+);(\d+);(\d+)([Mm])$/;
      onDataDisposable = term.onData((data) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        if (SGR_MOUSE_RE.test(data)) return;
        ws.send(data);
      });

      onResizeDisposable = term.onResize(({ cols, rows }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(`\x1b[RESIZE:${cols};${rows}]`);
        }
      });
    })();

    term.focus();

    return () => {
      unmounting = true;
      syncMetricsRef.current = null;
      onDataDisposable?.dispose();
      onResizeDisposable?.dispose();
      if (metricsDebounce) clearTimeout(metricsDebounce);
      window.removeEventListener("resize", scheduleSyncTerminalMetrics);
      window.visualViewport?.removeEventListener("resize", scheduleSyncTerminalMetrics);
      ro.disconnect();
      if (hostSyncRaf) cancelAnimationFrame(hostSyncRaf);
      if (settleRaf1) cancelAnimationFrame(settleRaf1);
      if (settleRaf2) cancelAnimationFrame(settleRaf2);
      clearReconnectTimer();
      wsRef.current?.close();
      wsRef.current = null;
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
      if (copyResetRef.current) {
        clearTimeout(copyResetRef.current);
        copyResetRef.current = null;
      }
    };
  }, [channel, clearReconnectTimer, resumeParam, scopedProfile, reconnectNonce, commandParam, onBannerChange, onReconnectNonceChange, onSessionEnd, onSessionTitleChange, searchParams, setSearchParams]);

  useEffect(() => {
    if (!isActive) return;
    let raf1 = 0;
    let raf2 = 0;
    raf1 = requestAnimationFrame(() => {
      raf1 = 0;
      raf2 = requestAnimationFrame(() => {
        raf2 = 0;
        syncMetricsRef.current?.();
        const host = hostRef.current;
        const active = typeof document !== "undefined" ? document.activeElement : null;
        const focusIsElsewhereInChatPage =
          active !== null &&
          active !== document.body &&
          host !== null &&
          !host.contains(active);
        if (!focusIsElsewhereInChatPage) {
          termRef.current?.focus();
        }
      });
    });
    return () => {
      if (raf1) cancelAnimationFrame(raf1);
      if (raf2) cancelAnimationFrame(raf2);
    };
  }, [isActive]);

  useEffect(() => {
    const term = termRef.current;
    if (!term) return;
    term.options.theme = terminalTheme;
  }, [terminalTheme]);

  return (
    <div
      className={cn(
        "relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg",
        "p-2 sm:p-3",
      )}
      style={{
        backgroundColor: terminalBg,
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      }}
    >
      <div
        ref={hostRef}
        className="hermes-chat-xterm-host min-h-0 min-w-0 flex-1"
      />

      {sessionEnded && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-black/60">
          <div className="text-sm tracking-wide text-white/80">
            Session ended.
          </div>
          <Button
            onClick={reconnect}
            prefix={<RotateCcw className="h-4 w-4" />}
            aria-label="Start a new chat session"
          >
            Start new session
          </Button>
        </div>
      )}

      <Button
        ghost
        onClick={handleCopyLast}
        title="Copy last assistant response as raw markdown"
        aria-label="Copy last assistant response"
        className={cn(
          "absolute z-10",
          "normal-case tracking-normal font-normal",
          "rounded border border-current/30",
          "bg-black/20",
          "opacity-70 hover:opacity-100 hover:border-current/60",
          "transition-opacity duration-150",
          "bottom-2 right-2 px-2 py-1 text-xs sm:bottom-3 sm:right-3 sm:px-2.5 sm:py-1.5",
          "lg:bottom-4 lg:right-4",
        )}
        style={{ color: terminalFg }}
      >
        <span className="inline-flex items-center gap-1.5">
          <Copy className="h-3 w-3 shrink-0" />
          <span className="hidden min-[400px]:inline tracking-wide">
            {copyState === "copied" ? "copied" : "copy last response"}
          </span>
        </span>
      </Button>
    </div>
  );
}
