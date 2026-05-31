import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  Building2,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  FlaskConical,
  FolderOpen,
  MessageSquare,
  Play,
} from "lucide-react";
import type { ComponentType } from "react";
import { api } from "@/lib/api";
import type { OpenStarAgent, AgentSkill } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { isDashboardEmbeddedChatEnabled } from "@/lib/dashboard-flags";

const AGENT_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  FileText,
  FlaskConical,
  Building2,
};

function resolveAgentIcon(name: string): ComponentType<{ className?: string }> {
  return AGENT_ICONS[name] ?? Bot;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<OpenStarAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { t } = useI18n();
  const { setAfterTitle } = usePageHeader();
  const navigate = useNavigate();
  const embeddedChat = isDashboardEmbeddedChatEnabled();
  const { toast, showToast } = useToast();

  const loadAgents = useCallback(() => {
    api
      .getOpenStarAgents()
      .then((resp) => {
        setAgents(resp.agents);
        setError(null);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadAgents();
    const id = setInterval(loadAgents, 5000);
    return () => clearInterval(id);
  }, [loadAgents]);

  useEffect(() => {
    if (loading) {
      setAfterTitle(null);
      return;
    }
    setAfterTitle(
      <Badge tone="secondary" className="text-xs tabular-nums">
        {agents.length}
      </Badge>,
    );
    return () => {
      setAfterTitle(null);
    };
  }, [loading, setAfterTitle, agents.length]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Bot className="h-8 w-8 mb-3 opacity-40" />
        <p className="text-sm font-medium">{t.agents.loadFailed}</p>
        <p className="text-xs mt-1 text-text-tertiary">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex min-w-0 w-full max-w-full flex-col gap-4">
      <Toast toast={toast} />
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">{t.agents.title}</CardTitle>
          </div>
        </CardHeader>

        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const Icon = resolveAgentIcon(agent.icon);
            const statusBadge = getStatusBadge(agent.status, t);
            const isExpanded = expandedId === agent.id;

            return (
              <div
                key={agent.id}
                className={`border transition-colors ${
                  isExpanded
                    ? "border-primary/30 bg-primary/[0.03] sm:col-span-3"
                    : "border-border hover:border-primary/20"
                }`}
              >
                <div
                  className="flex cursor-pointer flex-col items-center gap-2 p-4 transition-colors hover:bg-secondary/30"
                  onClick={() =>
                    setExpandedId((prev) =>
                      prev === agent.id ? null : agent.id,
                    )
                  }
                >
                  <Icon className="h-6 w-6 text-primary" />
                  <div className="flex flex-col items-center gap-1 text-center">
                    <span className="font-mondwest normal-case text-sm font-medium">
                      {agent.name}
                    </span>
                    <span className="font-mondwest normal-case text-xs text-muted-foreground">
                      {agent.description}
                    </span>
                    {agent.last_active && (
                      <span className="font-mondwest normal-case text-xs text-text-tertiary">
                        {t.agents.lastActive}: {timeAgo(agent.last_active)}
                      </span>
                    )}
                  </div>
                  <Badge
                    tone={statusBadge.tone}
                    className="mt-1"
                  >
                    {statusBadge.pulse && (
                      <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                    )}
                    {statusBadge.label}
                  </Badge>
                </div>

                {isExpanded && (
                  <AgentDetailPanel
                    agent={agent}
                    embeddedChat={embeddedChat}
                    onStartChat={() =>
                      navigate(
                        `/chat?command=${encodeURIComponent("/" + agent.id)}`,
                      )
                    }
                    onModelChange={() => {
                      console.log("[OpenStar] Model switch not yet implemented for agent:", agent.id);
                      showToast(t.agents.modelSwitchNotImplemented, "error");
                    }}
                    t={t}
                  />
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function AgentDetailPanel({
  agent,
  embeddedChat,
  onStartChat,
  onModelChange,
  t,
}: {
  agent: OpenStarAgent;
  embeddedChat: boolean;
  onStartChat: () => void;
  onModelChange: () => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const [selectedModel, setSelectedModel] = useState(agent.model);

  return (
    <div className="border-t border-border bg-background/50 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex items-center gap-2 text-sm">
          <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">{t.agents.model}:</span>
          <Select
            value={selectedModel}
            onValueChange={(val) => {
              setSelectedModel(val);
              onModelChange();
            }}
            className="h-7 text-xs min-w-[10rem]"
          >
            {agent.available_models.map((m) => (
              <SelectOption key={m} value={m}>
                {m}
              </SelectOption>
            ))}
          </Select>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <Play className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">
            {t.agents.currentTask}:
          </span>
          <span className="text-xs">
            {agent.current_task ?? t.agents.noActiveTask}
          </span>
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <MessageSquare className="h-3.5 w-3.5" />
          <span>{t.agents.recentActions}</span>
        </div>
        {agent.recent_actions.length > 0 ? (
          <ul className="ml-6 list-disc text-xs text-text-secondary space-y-0.5">
            {agent.recent_actions.slice(0, 5).map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ul>
        ) : (
          <p className="ml-6 text-xs text-text-tertiary">
            {t.agents.noRecentActivity}
          </p>
        )}
      </div>

      {/* Knowledge Layer */}
      <div className="mt-4 border-t border-border pt-3">
        <div className="flex items-center gap-2 text-sm font-medium mb-2">
          <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{t.agents.knowledge}</span>
        </div>

        <div className="space-y-1">
          {agent.knowledge.skills.map((skill) => (
            <SkillEntry key={skill.name} skill={skill} t={t} />
          ))}

          <div className="flex items-center gap-2 p-2 text-xs">
            <Badge tone="outline" className="text-[0.625rem] px-1.5 py-0">
              {t.agents.memoryLabel}
            </Badge>
            <span className="text-text-secondary">
              {agent.knowledge.memory_summary}
            </span>
          </div>
        </div>
      </div>

      {embeddedChat && (
        <div className="mt-4 flex items-center gap-2">
          <Button size="sm" onClick={onStartChat}>
            <MessageSquare className="h-3.5 w-3.5 mr-1.5" />
            {t.agents.startChat}
          </Button>
          <span className="text-xs text-text-tertiary">/{agent.id}</span>
        </div>
      )}
    </div>
  );
}

function SkillEntry({
  skill,
  t,
}: {
  skill: AgentSkill;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border/50">
      <div
        className="flex items-center gap-2 p-2 cursor-pointer hover:bg-secondary/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
        <span className="font-mono text-xs font-medium">{skill.name}</span>
      </div>

      {expanded && (
        <div className="border-t border-border/50 p-3 space-y-3">
          {/* L0 */}
          <div>
            <Badge tone="secondary" className="text-[0.625rem] px-1.5 py-0 mb-1">
              {t.agents.l0Label}
            </Badge>
            <p className="text-xs text-text-secondary ml-1">
              {skill.l0_summary}
            </p>
          </div>

          {/* L1 */}
          {skill.l1.categories.length > 0 && (
            <div>
              <Badge
                tone="warning"
                className="text-[0.625rem] px-1.5 py-0 mb-1"
              >
                {t.agents.l1Label}
              </Badge>
              <div className="ml-1 space-y-1">
                {skill.l1.categories.map((cat) => (
                  <div key={cat.name}>
                    <span className="text-xs font-medium text-warning">
                      {cat.name}/
                    </span>
                    <div className="ml-3 flex flex-wrap gap-1 mt-0.5">
                      {cat.files.map((f) => (
                        <span
                          key={f}
                          className="text-[0.625rem] text-text-tertiary bg-warning/5 px-1 py-0.5"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* L2 */}
          {skill.l2.modules.length > 0 && (
            <div>
              <Badge
                tone="success"
                className="text-[0.625rem] px-1.5 py-0 mb-1"
              >
                {t.agents.l2Label}
              </Badge>
              <div className="ml-1 space-y-1">
                {skill.l2.modules.map((mod) => (
                  <div key={mod.name}>
                    <span className="text-xs font-medium text-success">
                      {mod.name}/
                    </span>
                    <div className="ml-3 flex flex-wrap gap-1 mt-0.5">
                      {mod.files.map((f) => (
                        <span
                          key={f}
                          className="text-[0.625rem] text-text-tertiary bg-success/5 px-1 py-0.5"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getStatusBadge(
  status: OpenStarAgent["status"],
  t: ReturnType<typeof useI18n>["t"],
): { tone: "success" | "warning" | "outline"; label: string; pulse: boolean } {
  switch (status) {
    case "online":
      return { tone: "success", label: t.agents.online, pulse: true };
    case "busy":
      return { tone: "warning", label: t.agents.busy, pulse: false };
    case "offline":
    default:
      return { tone: "outline", label: t.agents.offline, pulse: false };
  }
}
