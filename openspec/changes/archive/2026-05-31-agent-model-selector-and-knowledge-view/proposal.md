## Why

Agents 详情面板中需要两个关键功能：(1) Model 选择器，允许用户看到并选择不同 LLM 模型（V1 先 mock 数据，选择后不生效，留出接口后续实现）；(2) 知识层可视化，让用户直观了解每个 Agent 的知识体系结构——L0（SKILL.md 标准工作流）、L1（架构/规范知识）、L2（模块专属知识），以及 Agent Memory。这对于理解 Agent 能力边界、排查 Agent 产出质量问题至关重要。

## What Changes

- Agent 详情面板中的 Model 字段从纯文本改为下拉选择器（Select 组件）
- 后端 API 新增 `available_models` 字段返回可选模型列表（mock 数据）
- 选择模型后调用占位函数（V1 不实际生效，仅 toast 提示）
- Agent 详情面板新增 "Knowledge" 标签/区域，展示该 Agent 的知识层
- 知识层展示结构：
  - Skills 列表，每个 Skill 下清晰展示 L0 (SKILL.md 摘要)、L1 (架构/规范文件树)、L2 (模块列表)
  - Agent Memory (MEMORY.md 摘要)
- 后端 API 新增 `knowledge` 字段返回结构化的知识层数据（V1 为 mock 数据）

## Capabilities

### New Capabilities
- `agent-model-selector`: Agent 详情面板中的模型下拉选择器，含可选模型列表和占位切换函数
- `agent-knowledge-view`: Agent 详情面板中的知识层可视化，分层展示 L0/L1/L2 和 Memory

### Modified Capabilities
<!-- No existing specs modified -->

## Impact

- **前端**: `web/src/pages/AgentsPage.tsx` — 详情面板扩展：模型选择器 + 知识层展示区域
- **后端 API**: `/api/openstar/agents` — 扩展返回 `available_models` 和 `knowledge` 字段
- **API 类型**: `web/src/lib/api.ts` — TypeScript 接口扩展
- **国际化**: 新增知识层相关翻译 key
- **无新外部依赖**: 复用现有 `@nous-research/ui` Select/Badge/Card 组件
