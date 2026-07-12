export type MessageRole = "user" | "assistant" | "system";

export type ToolCallStatus = "pending" | "running" | "done" | "error";

export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  status: ToolCallStatus;
  result?: string;
  error?: string;
  logs?: string[];
  startedAt?: number;
  completedAt?: number;
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "tool_use"; toolCall: ToolCall };

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: ContentBlock[];
  timestamp: number;
  isStreaming?: boolean;
}

export interface StreamEvent {
  type:
    | "message_start"
    | "content_delta"
    | "tool_use_start"
    | "tool_use_delta"
    | "tool_result"
    | "message_end";
  messageId?: string;
  role?: MessageRole;
  delta?: string;
  toolCall?: Partial<ToolCall>;
  timestamp?: number;
}
