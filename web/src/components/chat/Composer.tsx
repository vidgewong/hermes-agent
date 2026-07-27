import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { Send } from "lucide-react";
import { RuntimeSwitcher } from "@/components/RuntimeSwitcher";

interface ComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function Composer({ onSend, disabled }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  return (
    <div className="border-t border-border bg-background-base px-4 py-3">
      <div className="flex items-stretch gap-2">
        <RuntimeSwitcher badgeMode dropUp />
        <div
          className={cn(
            "flex min-w-0 flex-1 items-end gap-2 rounded-xl border border-border bg-secondary/20 px-3 py-2",
            "focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20",
            "transition-colors",
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={disabled}
            rows={1}
            className={cn(
              "flex-1 resize-none bg-transparent text-sm text-foreground",
              "placeholder:text-muted-foreground",
              "outline-none",
              "max-h-[200px] min-h-[24px]",
            )}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
              "transition-colors",
              value.trim() && !disabled
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-secondary text-muted-foreground",
            )}
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
        Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
