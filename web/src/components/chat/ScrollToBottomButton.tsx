import { cn } from "@/lib/utils";
import { ArrowDown } from "lucide-react";

interface ScrollToBottomButtonProps {
  onClick: () => void;
}

export function ScrollToBottomButton({ onClick }: ScrollToBottomButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "absolute bottom-4 left-1/2 -translate-x-1/2",
        "flex h-8 w-8 items-center justify-center rounded-full",
        "border border-border bg-background-base shadow-md",
        "text-muted-foreground hover:text-foreground hover:bg-secondary/50",
        "transition-colors",
      )}
      aria-label="Scroll to bottom"
    >
      <ArrowDown className="h-4 w-4" />
    </button>
  );
}
