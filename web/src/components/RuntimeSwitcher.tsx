import type React from "react";
import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { Cpu, Check, BotMessageSquare, CodeXml } from "lucide-react";
import { Button } from "@nous-research/ui/ui/components/button";
import { BottomSheet } from "@nous-research/ui/ui/components/bottom-sheet";
import { Typography } from "@nous-research/ui/ui/components/typography/index";
import { useBelowBreakpoint } from "@nous-research/ui/hooks/use-below-breakpoint";
import { useI18n } from "@/i18n/context";
import { cn } from "@/lib/utils";
import { fetchJSON } from "@/lib/api";

type AgentCoreId = "native" | "claude_code_sdk" | "codex_app_server";

interface AgentCoreOption {
  id: AgentCoreId;
  label: string;
  description: string;
}

const AGENT_CORES: AgentCoreOption[] = [
  { id: "native", label: "Hermes Native", description: "Default agent loop" },
  { id: "claude_code_sdk", label: "Claude Code", description: "Claude Agent SDK" },
  { id: "codex_app_server", label: "Codex", description: "OpenAI Codex runtime" },
];

const BADGE_STYLES: Record<AgentCoreId, {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}> = {
  native: {
    label: "Hermes",
    icon: Cpu,
    color: "text-text-secondary bg-secondary/40 border-border",
  },
  claude_code_sdk: {
    label: "Claude Code",
    icon: BotMessageSquare,
    color: "text-[#da7756] bg-[#da7756]/10 border-[#da7756]/30",
  },
  codex_app_server: {
    label: "Codex",
    icon: CodeXml,
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30",
  },
};

interface RuntimeSwitcherProps {
  collapsed?: boolean;
  dropUp?: boolean;
  /** When true, renders as a compact vertical badge beside the composer instead of the toolbar button. */
  badgeMode?: boolean;
}

export function RuntimeSwitcher({ collapsed = false, dropUp = false, badgeMode = false }: RuntimeSwitcherProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<AgentCoreId>("native");
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const narrowViewport = useBelowBreakpoint(640);
  const useMobileSheet = Boolean(dropUp && narrowViewport);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    fetchJSON<{ agent_core: AgentCoreId }>("/api/agent-core")
      .then(({ agent_core }) => setCurrent(agent_core))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  useEffect(() => {
    if (!open || useMobileSheet) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (containerRef.current?.contains(target)) return;
      if (dropdownRef.current?.contains(target)) return;
      close();
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open, close, useMobileSheet]);

  const handleSelect = async (id: AgentCoreId) => {
    if (id === current) { close(); return; }
    setLoading(true);
    try {
      await fetchJSON<{ ok: boolean }>("/api/agent-core", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_core: id }),
      });
      setCurrent(id);
    } catch (e) {
      console.error("Failed to switch agent core:", e);
    } finally {
      setLoading(false);
      close();
    }
  };

  const currentRuntime = AGENT_CORES.find((r) => r.id === current) ?? AGENT_CORES[0];
  const badge = BADGE_STYLES[current];
  const sheetTitle = "Agent Core";

  return (
    <div ref={containerRef} className="relative inline-flex">
      {badgeMode ? (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          disabled={loading}
          title={`Agent Core: ${currentRuntime.label} — click to switch`}
          aria-label="Switch agent core"
          aria-expanded={open}
          aria-haspopup="listbox"
          className={cn(
            "flex w-[4.5rem] shrink-0 flex-col items-center justify-center gap-1 rounded-lg border px-2",
            "text-[9px] font-medium leading-none tracking-wide",
            "transition-opacity hover:opacity-75",
            badge.color,
          )}
        >
          <badge.icon className="h-3.5 w-3.5 shrink-0" />
          <span className="whitespace-nowrap">{badge.label}</span>
        </button>
      ) : (
        <Button
          ghost
          size={collapsed ? "icon" : undefined}
          onClick={() => setOpen((o) => !o)}
          disabled={loading}
          className={cn(
            collapsed
              ? "text-text-secondary hover:text-foreground hover:bg-transparent"
              : "px-2 py-1 normal-case tracking-normal font-normal text-xs text-text-secondary hover:text-foreground",
          )}
          title={`Agent Core: ${currentRuntime.label}`}
          aria-label="Switch agent core"
          aria-expanded={open}
          aria-haspopup="listbox"
        >
          <span className="inline-flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5" />
            {!collapsed && (
              <Typography className="hidden sm:inline text-xs">
                {currentRuntime.label}
              </Typography>
            )}
          </span>
        </Button>
      )}

      {useMobileSheet && (
        <BottomSheet
          backdropDismissLabel={t.common.close}
          onClose={close}
          open={open}
          title={sheetTitle}
        >
          <div aria-label={sheetTitle} role="listbox">
            <AgentCoreOptions
              cores={AGENT_CORES}
              current={current}
              onSelect={handleSelect}
            />
          </div>
        </BottomSheet>
      )}

      {open && !useMobileSheet && (() => {
        const rect = containerRef.current?.getBoundingClientRect();
        const dropdown = (
          <div
            ref={dropdownRef}
            aria-label={sheetTitle}
            className={cn(
              "min-w-[12rem] border border-border bg-popover shadow-md py-1 max-h-80 overflow-y-auto",
              dropUp ? "fixed z-[100]" : "absolute z-50 right-0 top-full mt-1",
            )}
            role="listbox"
            style={
              dropUp && rect
                ? { bottom: window.innerHeight - rect.top + 4, left: rect.left }
                : undefined
            }
          >
            <AgentCoreOptions
              cores={AGENT_CORES}
              current={current}
              onSelect={handleSelect}
            />
          </div>
        );
        return dropUp ? createPortal(dropdown, document.body) : dropdown;
      })()}
    </div>
  );
}

function AgentCoreOptions({
  cores,
  current,
  onSelect,
}: {
  cores: AgentCoreOption[];
  current: AgentCoreId;
  onSelect: (id: AgentCoreId) => void;
}) {
  return (
    <>
      {cores.map((rt) => {
        const selected = rt.id === current;
        return (
          <button
            aria-selected={selected}
            className={cn(
              "w-full text-left px-3 py-2 flex items-center gap-2 cursor-pointer",
              "text-xs",
              "hover:bg-accent hover:text-accent-foreground transition-colors",
              selected ? "font-semibold text-foreground" : "text-muted-foreground",
            )}
            key={rt.id}
            onClick={() => onSelect(rt.id)}
            role="option"
            type="button"
          >
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="truncate font-medium">{rt.label}</span>
              <span className="truncate text-[10px] opacity-60">{rt.description}</span>
            </div>
            {selected && <Check className="ml-auto h-3 w-3 shrink-0 text-midground" />}
          </button>
        );
      })}
    </>
  );
}
