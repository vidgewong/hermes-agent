import { useState } from "react";
import { cn } from "@/lib/utils";
import type { ToolCall, ToolCallStatus } from "@/lib/chat-message-types";
import { ChevronDown, ChevronRight, Wrench, Loader2, Check, AlertCircle } from "lucide-react";

interface ToolCardProps {
  toolCall: ToolCall;
}

export function ToolCard({ toolCall }: ToolCardProps) {
  const [expanded, setExpanded] = useState(toolCall.status === "error");

  return (
    <div
      className={cn(
        "my-2 rounded-lg border text-xs",
        toolCall.status === "error"
          ? "border-destructive/40 bg-destructive/5"
          : "border-border bg-secondary/30",
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-secondary/20 transition-colors rounded-lg"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
        )}
        <Wrench className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="flex-1 font-medium truncate">{toolCall.name}</span>
        <StatusBadge status={toolCall.status} />
      </button>

      {expanded && (
        <div className="border-t border-border/50 px-3 py-2 space-y-2">
          {toolCall.arguments && (
            <div>
              <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                Input
              </div>
              <pre className="bg-secondary/40 rounded px-2 py-1.5 text-[11px] overflow-x-auto whitespace-pre-wrap break-all font-mono">
                {formatJson(toolCall.arguments)}
              </pre>
            </div>
          )}

          {toolCall.result && (
            <div>
              <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                Output
              </div>
              <pre className="bg-secondary/40 rounded px-2 py-1.5 text-[11px] overflow-x-auto whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto">
                {formatJson(toolCall.result)}
              </pre>
            </div>
          )}

          {toolCall.error && (
            <div>
              <div className="text-[10px] font-medium text-destructive uppercase tracking-wider mb-1">
                Error
              </div>
              <pre className="bg-destructive/10 text-destructive rounded px-2 py-1.5 text-[11px] whitespace-pre-wrap break-all font-mono">
                {toolCall.error}
              </pre>
            </div>
          )}

          {toolCall.logs && toolCall.logs.length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                Logs
              </div>
              <pre className="bg-secondary/40 rounded px-2 py-1.5 text-[11px] overflow-x-auto whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                {toolCall.logs.join("\n")}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: ToolCallStatus }) {
  switch (status) {
    case "pending":
      return (
        <span className="inline-flex items-center gap-1 text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-pulse" />
          pending
        </span>
      );
    case "running":
      return (
        <span className="inline-flex items-center gap-1 text-blue-500">
          <Loader2 className="h-3 w-3 animate-spin" />
          running
        </span>
      );
    case "done":
      return (
        <span className="inline-flex items-center gap-1 text-green-600">
          <Check className="h-3 w-3" />
          done
        </span>
      );
    case "error":
      return (
        <span className="inline-flex items-center gap-1 text-destructive">
          <AlertCircle className="h-3 w-3" />
          error
        </span>
      );
  }
}

function formatJson(str: string): string {
  try {
    return JSON.stringify(JSON.parse(str), null, 2);
  } catch {
    return str;
  }
}
