import { useEffect, useState } from "react";
import { fetchJSON } from "@/lib/api";

export type AgentCoreId = "native" | "claude_code_sdk" | "codex_app_server";

export function useAgentCore() {
  const [agentCore, setAgentCore] = useState<AgentCoreId>("native");

  useEffect(() => {
    fetchJSON<{ agent_core: AgentCoreId }>("/api/agent-core")
      .then(({ agent_core }) => setAgentCore(agent_core))
      .catch(() => {});
  }, []);

  return agentCore;
}
