import { useCallback, useEffect, useRef, useState } from "react";
import { api, type SessionMessage } from "@/lib/api";
import type { ChatMessage, ContentBlock, ToolCall, StreamEvent } from "@/lib/chat-message-types";

function convertSessionMessage(msg: SessionMessage, index: number): ChatMessage | null {
  if (msg.role === "tool") return null;

  const blocks: ContentBlock[] = [];

  if (msg.content) {
    blocks.push({ type: "text", text: msg.content });
  }

  if (msg.tool_calls) {
    for (const tc of msg.tool_calls) {
      const toolCall: ToolCall = {
        id: tc.id,
        name: tc.function.name,
        arguments: tc.function.arguments,
        status: "done",
      };
      blocks.push({ type: "tool_use", toolCall });
    }
  }

  if (blocks.length === 0) return null;

  const role = msg.role === "system" ? "assistant" : msg.role;
  if (role !== "user" && role !== "assistant") return null;

  return {
    id: `msg-${index}`,
    role,
    content: blocks,
    timestamp: msg.timestamp ?? Date.now() / 1000,
  };
}

export function useChatMessages(
  sessionId: string | null,
  profile: string,
  onSessionCreated?: (id: string) => void,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const onSessionCreatedRef = useRef(onSessionCreated);
  onSessionCreatedRef.current = onSessionCreated;

  const fetchMessages = useCallback(async () => {
    if (!sessionId) {
      // Don't clear messages — there may be optimistic/streaming messages
      // from a new conversation that hasn't been persisted yet.
      return;
    }
    try {
      setIsLoading(true);
      const res = await api.getSessionMessages(sessionId, profile);
      const converted = res.messages
        .map(convertSessionMessage)
        .filter((m): m is ChatMessage => m !== null);
      setMessages(converted);
    } catch {
      // Best-effort
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, profile]);

  // On mount / sessionId change: check if the session is still active so we
  // can show a streaming indicator immediately while the WS reconnects.
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    api.getSessionDetail(sessionId, profile)
      .then((info) => {
        if (cancelled) return;
        if (info.is_active) setIsStreaming(true);
      })
      .catch(() => {});

    return () => { cancelled = true; };
  }, [sessionId, profile]);

  // On mount / sessionId change: fetch immediately, then poll a few more times
  // to catch responses that were still streaming when we switched away.
  // After the final poll, clear any stale isStreaming flag in case message_end
  // was missed while the component was unmounted.
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    const POLL_INTERVALS = [0, 1000, 2000, 4000, 8000];
    const last = POLL_INTERVALS[POLL_INTERVALS.length - 1];

    POLL_INTERVALS.forEach((delay) => {
      setTimeout(async () => {
        if (cancelled) return;
        await fetchMessages();
        if (!cancelled && delay === last) {
          setIsStreaming(false);
        }
      }, delay);
    });

    return () => { cancelled = true; };
  }, [fetchMessages, sessionId]);

  // Connect WebSocket for streaming — rebuilt whenever sessionId or profile changes.
  useEffect(() => {
    let ws: WebSocket | null = null;
    let cancelled = false;

    async function connect() {
      const params: Record<string, string> = {};
      if (sessionIdRef.current) params.session = sessionIdRef.current;
      if (profile) params.profile = profile;
      const url = await api.buildWsUrl("/api/chat/stream", params);
      if (cancelled) return;

      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const event: StreamEvent & Record<string, unknown> = JSON.parse(ev.data);
          handleStreamEvent(event);
        } catch {}
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!cancelled) {
          setTimeout(() => {
            if (!cancelled) connect();
          }, 3000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      ws?.close();
      wsRef.current = null;
    };
  // Re-connect when sessionId changes so the WS is always bound to the current session.
  }, [profile, sessionId]);

  const handleStreamEvent = useCallback((event: StreamEvent & Record<string, unknown>) => {
    switch (event.type) {
      case "message_start": {
        setIsStreaming(true);
        const newMsg: ChatMessage = {
          id: (event.messageId as string) || `stream-${Date.now()}`,
          role: (event.role as "assistant") || "assistant",
          content: [{ type: "text", text: "" }],
          timestamp: Date.now() / 1000,
          isStreaming: true,
        };
        setMessages((prev) => [...prev, newMsg]);
        break;
      }
      case "content_delta": {
        const delta = event.delta as string;
        if (!delta) break;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || !last.isStreaming) return prev;
          const updated = { ...last, content: [...last.content] };
          const lastBlock = updated.content[updated.content.length - 1];
          if (lastBlock && lastBlock.type === "text") {
            updated.content[updated.content.length - 1] = {
              type: "text",
              text: lastBlock.text + delta,
            };
          } else {
            updated.content.push({ type: "text", text: delta });
          }
          return [...prev.slice(0, -1), updated];
        });
        break;
      }
      case "tool_use_start": {
        const tc = event.toolCall as Partial<ToolCall>;
        if (!tc) break;
        const toolCall: ToolCall = {
          id: tc.id || `tool-${Date.now()}`,
          name: tc.name || "unknown",
          arguments: tc.arguments || "",
          status: "running",
        };
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || !last.isStreaming) return prev;
          const updated = { ...last, content: [...last.content, { type: "tool_use" as const, toolCall }] };
          return [...prev.slice(0, -1), updated];
        });
        break;
      }
      case "tool_use_delta": {
        const tc = event.toolCall as { id?: string; log?: string } | undefined;
        if (!tc?.id || !tc?.log) break;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || !last.isStreaming) return prev;
          const updated = { ...last, content: [...last.content] };
          for (let i = updated.content.length - 1; i >= 0; i--) {
            const block = updated.content[i];
            if (block.type === "tool_use" && block.toolCall.id === tc.id) {
              updated.content[i] = {
                type: "tool_use",
                toolCall: {
                  ...block.toolCall,
                  logs: [...(block.toolCall.logs || []), tc.log!],
                },
              };
              break;
            }
          }
          return [...prev.slice(0, -1), updated];
        });
        break;
      }
      case "tool_result": {
        const tc = event.toolCall as Partial<ToolCall> | undefined;
        if (!tc?.id) break;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || !last.isStreaming) return prev;
          const updated = { ...last, content: [...last.content] };
          for (let i = updated.content.length - 1; i >= 0; i--) {
            const block = updated.content[i];
            if (block.type === "tool_use" && block.toolCall.id === tc.id) {
              updated.content[i] = {
                type: "tool_use",
                toolCall: {
                  ...block.toolCall,
                  status: tc.status || "done",
                  result: tc.result,
                  error: tc.error,
                },
              };
              break;
            }
          }
          return [...prev.slice(0, -1), updated];
        });
        break;
      }
      case "message_end": {
        setIsStreaming(false);
        const endedSessionId = (event as Record<string, unknown>).sessionId as string | undefined;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || !last.isStreaming) return prev;
          const updated = { ...last, isStreaming: false };
          return [...prev.slice(0, -1), updated];
        });
        if (endedSessionId && !sessionIdRef.current) {
          onSessionCreatedRef.current?.(endedSessionId);
        }
        // Refresh from server to get canonical state
        setTimeout(() => fetchMessages(), 500);
        break;
      }
    }
  }, [fetchMessages]);

  const sendMessage = useCallback((content: string) => {
    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: [{ type: "text", text: content }],
      timestamp: Date.now() / 1000,
    };
    setMessages((prev) => [...prev, userMsg]);

    // Send via WebSocket
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "send_message", content }));
    }
  }, []);

  return { messages, isStreaming, isLoading, sendMessage, refetch: fetchMessages };
}
