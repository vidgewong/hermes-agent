import { cn } from "@/lib/utils";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import { useChatMessages } from "@/hooks/useChatMessages";

interface ConversationalViewProps {
  isActive?: boolean;
  sessionId: string | null;
  profile: string;
  onSend?: (message: string) => void;
  onSessionCreated?: (id: string) => void;
}

function MessageSkeleton() {
  return (
    <div className="flex flex-col gap-4 px-4 py-6">
      {[...Array(4)].map((_, i) => (
        <div key={i} className={cn("flex gap-3", i % 2 === 0 ? "flex-row" : "flex-row-reverse")}>
          <div className="h-7 w-7 rounded-full bg-secondary/60 animate-pulse" />
          <div className={cn("flex flex-col gap-1.5", i % 2 === 0 ? "items-start" : "items-end")}>
            <div className="h-10 rounded-2xl bg-secondary/40 animate-pulse" style={{ width: `${120 + i * 40}px` }} />
            <div className="h-3 w-12 rounded bg-secondary/20 animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ConversationalView({
  sessionId,
  profile,
  onSessionCreated,
}: ConversationalViewProps) {
  const { messages, isStreaming, isLoading, sendMessage } = useChatMessages(sessionId, profile, onSessionCreated);

  return (
    <div
      className={cn(
        "relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg",
        "bg-background-base",
      )}
    >
      {isLoading && messages.length === 0 ? (
        <MessageSkeleton />
      ) : (
        <MessageList messages={messages} isStreaming={isStreaming} />
      )}
      <Composer onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
