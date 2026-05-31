## Context

AgentsPage 当前的详情面板显示 model 为纯文本。需要改为可交互的下拉选择器，并新增知识层可视化区域。知识层结构参考技术方案文档：每个 Agent 有多个 Skills，每个 Skill 内部分 L0 (SKILL.md)、L1 (references/L1/ 跨模块通用知识)、L2 (references/L2/ 模块专属知识)。Agent 还有独立的 Memory。

现有组件库 `@nous-research/ui` 提供了 Select 组件可直接使用。

## Goals / Non-Goals

**Goals:**
- Model 字段改为下拉选择器，列出可用模型
- 选择模型后调用占位函数（console.log + toast 提示 "Model switch not yet implemented"）
- 新增知识层展示区域，用树状/层级结构清晰展示 L0、L1、L2 和 Memory
- L1 展示其子目录结构（architecture/, aspice/, writing-rules/ 等）
- L2 展示已支持的模块列表（audio, adas 等）
- Memory 展示简要摘要
- 所有数据从 API mock 返回（V1），结构设计为后续接入真实文件系统做准备

**Non-Goals:**
- 不实现真实的模型切换逻辑
- 不读取真实文件系统中的 Skill/Memory 文件内容
- 不实现知识层的编辑/修改功能
- 不实现 L3 (用户个人记忆) 展示

## Decisions

### 1. Model 选择器 — 使用 Select 组件 + 占位回调

**决定**: 使用 `@nous-research/ui` 的 Select 组件。`onChange` 回调中仅 console.log + toast 提示，不调用后端。后端返回 `available_models: string[]` 列表。

**理由**: 保持接口设计正确，但不引入尚未实现的后端逻辑。Toast 给用户明确反馈"功能待实现"。

### 2. 知识层数据结构 — 结构化 JSON

**决定**: 后端返回每个 agent 的 `knowledge` 对象：
```json
{
  "skills": [
    {
      "name": "requirement-generation",
      "l0_summary": "从系统需求生成软件需求...",
      "l1": {
        "categories": [
          { "name": "architecture", "files": ["system-overview.md", "qnx-android-split.md"] },
          { "name": "aspice", "files": ["swe1-process.md", "qa-attributes.md"] }
        ]
      },
      "l2": {
        "modules": [
          { "name": "audio", "files": ["audio-module-rules.md", "codec-constraints.md"] },
          { "name": "adas", "files": ["safety-levels.md", "sensor-interfaces.md"] }
        ]
      }
    }
  ],
  "memory_summary": "12 条经验记录，最近更新于 2026-05-20"
}
```

**理由**: 结构化数据让前端能灵活渲染不同层级。后续接入真实文件系统时只需替换数据源，结构不变。

### 3. 知识层 UI — 可折叠层级视图

**决定**: 知识层展示为可折叠的层级结构。顶层是 Skills 列表和 Memory。每个 Skill 展开后显示 L0 摘要、L1 分类列表、L2 模块列表。使用颜色编码区分层级（L0=primary, L1=warning, L2=success）。

**理由**: 清晰的层级结构让用户一眼看懂知识体系。折叠避免信息过载。颜色编码快速区分不同层级的知识类型。

### 4. Mock 数据 — 后端固定配置

**决定**: 在 `_OPENSTAR_AGENTS` 中为每个 Agent 配置不同的 mock knowledge 数据，体现各 Agent 的领域差异。`available_models` 返回固定列表。

**理由**: 不同 Agent 有不同知识结构，mock 数据应体现这一点（如 REQ Agent 有 writing-rules, Test Agent 有 test-framework 等）。

## Risks / Trade-offs

- **[Mock 数据结构与真实不匹配]** → 后续接入真实文件系统时可能需要调整 JSON 结构。但核心层级概念（L0/L1/L2/Memory）不会变。
- **[知识层信息量大]** → 折叠 UI 缓解。初始状态全部折叠，用户按需展开。
- **[Select 组件可用性]** → 需确认 `@nous-research/ui` 的 Select 支持 controlled mode。如不支持则降级为原生 `<select>`。
