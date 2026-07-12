import { cn } from "@/lib/utils";
import { Markdown } from "@/components/Markdown";
import { ToolCard } from "./ToolCard";
import type { ChatMessage } from "@/lib/chat-message-types";
import { User, Bot } from "lucide-react";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-2",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary/10 text-primary"
            : "bg-secondary text-muted-foreground",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div
        className={cn(
          "flex max-w-[80%] flex-col gap-1",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5",
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : "bg-secondary/60 text-foreground rounded-bl-md",
          )}
        >
          {message.content.map((block, i) => {
            if (block.type === "text") {
              if (isUser) {
                return (
                  <p key={i} className="text-sm leading-relaxed whitespace-pre-wrap">
                    {block.text}
                  </p>
                );
              }
              return (
                <Markdown
                  key={i}
                  content={block.text}
                  streaming={message.isStreaming && i === message.content.length - 1}
                />
              );
            }
            if (block.type === "tool_use") {
              return <ToolCard key={i} toolCall={block.toolCall} />;
            }
            return null;
          })}
        </div>

        <span className="text-[10px] text-muted-foreground px-1">
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  );
}

function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}
