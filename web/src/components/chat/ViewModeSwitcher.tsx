import { cn } from "@/lib/utils";
import { Monitor, MessageSquare } from "lucide-react";
import type { ChatViewMode } from "@/hooks/useChatViewMode";

interface ViewModeSwitcherProps {
  mode: ChatViewMode;
  onModeChange: (mode: ChatViewMode) => void;
}

export function ViewModeSwitcher({ mode, onModeChange }: ViewModeSwitcherProps) {
  return (
    <div className="flex items-center gap-1 rounded-md border border-current/20 bg-midground/5 p-0.5 w-fit">
      <button
        type="button"
        onClick={() => onModeChange("tui")}
        className={cn(
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
          mode === "tui"
            ? "bg-midground/15 text-midground shadow-sm"
            : "text-midground/50 hover:text-midground/80",
        )}
      >
        <Monitor className="h-3.5 w-3.5" />
        Terminal
      </button>
      <button
        type="button"
        onClick={() => onModeChange("im")}
        className={cn(
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
          mode === "im"
            ? "bg-midground/15 text-midground shadow-sm"
            : "text-midground/50 hover:text-midground/80",
        )}
      >
        <MessageSquare className="h-3.5 w-3.5" />
        Chat
      </button>
    </div>
  );
}
