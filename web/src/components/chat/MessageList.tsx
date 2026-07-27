import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";
import { ScrollToBottomButton } from "./ScrollToBottomButton";
import type { ChatMessage } from "@/lib/chat-message-types";
import { MessageSquare } from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
}

export function MessageList({ messages }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      setIsAtBottom(true);
    }
  }, []);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const threshold = 60;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setIsAtBottom(atBottom);
  }, []);

  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom();
    }
  }, [messages.length, isAtBottom, scrollToBottom]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <MessageSquare className="h-10 w-10 opacity-30" />
        <p className="text-sm">Start a conversation</p>
      </div>
    );
  }

  let lastDate = "";

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className={cn(
          "flex-1 overflow-y-auto overflow-x-hidden",
          "py-4 space-y-1",
        )}
      >
        {messages.map((msg) => {
          const msgDate = new Date(msg.timestamp * 1000).toLocaleDateString();
          const showDate = msgDate !== lastDate;
          lastDate = msgDate;

          return (
            <div key={msg.id}>
              {showDate && (
                <div className="flex items-center justify-center py-2">
                  <span className="text-[10px] text-muted-foreground bg-secondary/40 px-2 py-0.5 rounded-full">
                    {msgDate}
                  </span>
                </div>
              )}
              <MessageBubble message={msg} />
            </div>
          );
        })}
      </div>

      {!isAtBottom && (
        <ScrollToBottomButton onClick={scrollToBottom} />
      )}
    </div>
  );
}
