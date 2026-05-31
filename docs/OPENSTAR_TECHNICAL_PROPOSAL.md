# OpenStar 技术方案：基于 Hermes Agent 的企业数字员工平台

**Version:** 3.0  
**Author:** Vidge  
**Date:** 2026-05-31  
**Status:** Technical Proposal

---

## 1. 核心概念模型

### 1.1 问题本质

OpenStar 的核心诉求是：**多个用户共用一个 Agent（如 REQ Agent），每个人在使用中产生的经验和修正，能否经审批后沉淀到这个 Agent 的知识里，让所有人受益。**

```
多个用户 ──使用──→ 同一个 Agent ──拥有──→ 分层知识 (Skill 内部分层)
    │                                           ↑
    └──修正/贡献──→ 审批流 ──通过后──→ 写入 ──────┘
```

### 1.2 Skill 的正确结构

参考 [agentskills.io](https://agentskills.io/home) 的标准：

> A skill is a folder containing a SKILL.md file. Skills can also bundle scripts, reference materials, templates, and other resources.

**一个 Skill 就是一个完整的能力单元：**

```
my-skill/
├── SKILL.md          # Required: metadata + instructions (这就是 L0)
├── scripts/          # Optional: executable code (按需加载)
├── references/       # Optional: documentation (L1 + L2 在这里分层)
├── assets/           # Optional: templates, resources
└── ...
```

### 1.3 知识分层在 Skill 内部

**分层不是在 skills/ 目录下建 L0/ L1/ L2/ 子文件夹，而是在每个 Skill 内部通过 `SKILL.md` + `references/` 来组织分层。**

```mermaid
graph TB
    subgraph "一个 Skill 的内部分层"
        L0[SKILL.md<br/>─────────<br/>L0: 标准工作流<br/>做什么、怎么做<br/>需要什么工具<br/>执行步骤]
        
        SCRIPTS[scripts/<br/>─────────<br/>按需加载的脚本<br/>工具调用代码]
        
        subgraph "references/ (分层知识)"
            L1[L1/<br/>─────────<br/>业务场景/架构知识<br/>跨模块共享<br/>专家/架构师维护]
            L1_SUB[L1/sub-topics/<br/>─────────<br/>L1 依赖的更多知识<br/>可继续嵌套]
            L2[L2/<br/>─────────<br/>按模块划分<br/>模块负责人维护]
        end
        
        ASSETS[assets/<br/>─────────<br/>模板、配置文件等]
    end
    
    L0 --> SCRIPTS
    L0 --> L1
    L1 --> L1_SUB
    L0 --> L2
```

**关键原则：**
- **SKILL.md 就是 L0** — 定义标准工作流（与用户无关，与模块无关）
- **references/L1/** — 架构/流程/规范知识，跨模块通用，架构师维护
- **references/L1/xxx/yyy/** — L1 依赖的子知识，继续在 L1 下嵌套
- **references/L2/** — 按模块分文件夹，各模块负责人维护
- **scripts/** — 工具脚本，按需加载
- **Agent 的 MEMORY.md** — Agent 级别积累经验（独立于 Skill，也属于 Agent）

### 1.4 完整的 Agent 知识体系

```mermaid
graph TB
    subgraph AGENT_KB["一个 Agent - 如 REQ Agent - 的完整知识体系"]
        SOUL["SOUL.md\nAgent 人格定义\n角色、边界、行为准则"]

        SKILL_A["requirement-generation/\nSKILL.md L0 + refs + scripts"]
        SKILL_B["dng-integration/\nSKILL.md L0 + refs + scripts"]
        SKILL_C["clarification-protocol/\nSKILL.md L0 + refs + scripts"]

        AGENT_MEM["memories/MEMORY.md\nAgent 积累的经验\n与用户无关"]
    end

    subgraph USER_LAYER["用户层 - 不属于 Agent"]
        USER_MEM["User Memory L3\n个人偏好/习惯"]
    end
```

---

## 2. Skill 内部结构详细设计

### 2.1 REQ Agent 的核心 Skill 示例

```
~/.hermes/profiles/req-agent/
├── SOUL.md                                    # Agent 人格 (与用户无关)
├── config.yaml                                # Agent 配置
├── memories/
│   └── MEMORY.md                              # Agent Memory (积累的经验)
│
└── skills/
    ├── requirement-generation/                 # Skill: 需求生成
    │   ├── SKILL.md                           # L0: 标准工作流
    │   ├── scripts/
    │   │   ├── validate-requirement.py        # 需求格式校验脚本
    │   │   └── trace-link-checker.py          # 追溯链检查脚本
    │   ├── references/
    │   │   ├── L1/                            # 业务场景知识 (架构师维护)
    │   │   │   ├── architecture/
    │   │   │   │   ├── system-overview.md     # 系统架构总览
    │   │   │   │   ├── qnx-android-split.md  # QNX+Android 分层
    │   │   │   │   └── communication/        # 通信相关 (L1 嵌套)
    │   │   │   │       ├── someip-rules.md
    │   │   │   │       ├── ipc-protocol.md
    │   │   │   │       └── interface-defs/
    │   │   │   │           ├── someip-api.yaml
    │   │   │   │           └── dbus-services.md
    │   │   │   ├── aspice/
    │   │   │   │   ├── swe1-process.md        # SWE.1 过程域规范
    │   │   │   │   └── qa-attributes.md       # QA 属性标准
    │   │   │   └── writing-rules/
    │   │   │       ├── requirement-format.md  # 需求写作规范
    │   │   │       └── shall-should-rules.md  # shall/should 用词规则
    │   │   │
    │   │   └── L2/                            # 模块专属知识 (模块负责人维护)
    │   │       ├── audio/
    │   │       │   ├── audio-module-rules.md  # 音频模块特定规则
    │   │       │   ├── codec-constraints.md   # 编解码器约束
    │   │       │   └── fade-timing.md         # 淡入淡出时序标准
    │   │       ├── adas/
    │   │       │   ├── safety-levels.md       # ASIL 安全等级
    │   │       │   └── sensor-interfaces.md   # 传感器接口规范
    │   │       └── health-monitor/
    │   │           ├── hm-requirements.md     # HM 模块需求模式
    │   │           └── watchdog-rules.md      # 看门狗相关规则
    │   │
    │   └── assets/
    │       └── templates/
    │           └── sw-requirement-template.md  # 软件需求模板
    │
    ├── dng-integration/                        # Skill: DNG 系统集成
    │   ├── SKILL.md                           # L0: DNG 操作流程
    │   ├── scripts/
    │   │   ├── dng-read.py                    # DNG REST API 读取
    │   │   └── dng-push.py                    # DNG 推送脚本
    │   └── references/
    │       ├── L1/
    │       │   ├── dng-api-guide.md           # DNG API 使用指南
    │       │   └── dng-pagination-quirks.md   # DNG 分页注意事项
    │       └── L2/
    │           ├── audio/
    │           │   └── audio-dng-views.md     # 音频模块 DNG 视图配置
    │           └── adas/
    │               └── adas-dng-views.md      # ADAS DNG 视图配置
    │
    └── clarification-protocol/                 # Skill: 澄清协议
        ├── SKILL.md                           # L0: 缺少信息时如何询问
        └── references/
            └── L1/
                └── common-missing-info.md     # 常见缺失信息模式
```

### 2.2 SKILL.md (L0) 示例

```markdown
---
name: requirement-generation
description: "Generate software requirements from system requirements following ASPICE SWE.1"
version: 1.2.0
metadata:
  hermes:
    tags: [aspice, swe1, requirements, dng]
    tools_required: [dng-read, dng-push, terminal]
    related_skills: [dng-integration, clarification-protocol]
---

# Requirement Generation (SWE.1)

## Overview
从系统需求生成完整的软件需求，遵循 ASPICE SWE.1 过程域标准。

## When to Use
- 用户请求生成/更新软件需求
- 检测到上游系统需求变更
- 模块初始化需要建立需求基线

## Prerequisites
- 系统需求已在 DNG 中就绪
- 用户已确认目标模块

## Workflow

### Step 1: 确认上下文
1. 确认目标模块 (从用户消息或 L3 memory 推断)
2. 从 references/L1/architecture/ 加载该模块对应的架构知识
3. 从 references/L2/{module}/ 加载模块专属规则
4. 如果缺少必要信息，使用 clarification-protocol Skill 询问

### Step 2: 摄取系统需求
1. 使用 dng-integration Skill 读取系统需求
2. 交叉引用 references/L1/architecture/system-overview.md
3. 识别该模块相关的系统需求子集

### Step 3: 生成软件需求
1. 按 references/L1/writing-rules/requirement-format.md 格式生成
2. 每条需求包含:
   - 唯一标识符
   - 需求描述 (遵循 shall/should 规则)
   - 追溯链 (关联的系统需求 ID)
   - 验证准则
   - 接口规格 (参考 L1/architecture/communication/)
3. 遵循 references/L2/{module}/ 中的模块特定约束

### Step 4: 质量检查
1. 运行 scripts/validate-requirement.py 检查格式合规
2. 运行 scripts/trace-link-checker.py 检查追溯完整性
3. 按 references/L1/aspice/qa-attributes.md 检查 QA 属性

### Step 5: 迭代确认
1. 向用户展示生成结果摘要
2. 接受用户修正
3. 修正后重新执行质量检查

### Step 6: 推送
1. 使用 dng-integration Skill 推送至 DNG (草案状态)
2. 通知用户完成情况

## Notes
- 生成过程中，如果检测到参考代码与新系统需求冲突，需标记并通知
- 优先级: 新系统需求 > 架构知识 > 参考代码
- 永远不自动提升到正式状态，仅产出草案
```

### 2.3 references/L1/ 内的嵌套示例

```markdown
# references/L1/architecture/communication/someip-rules.md

# SomeIP 通信规则

## 适用范围
所有跨进程、跨 ECU 的服务调用。

## 规则
1. 所有服务接口必须使用 SomeIP，禁止直接 TCP/UDP socket
2. Service Discovery 必须启用，不允许硬编码地址
3. Event 通知使用 SomeIP Event Group，不允许轮询
4. 序列化使用 SomeIP 原生序列化，不允许额外 Protobuf 层

## 接口定义
详见 interface-defs/someip-api.yaml

## 例外
- Android 内部组件间通信使用 AIDL/Binder
- 诊断通道使用 UDS (ISO 14229)

## 更新记录
- 2026-05-15: 架构师 Zhang 确认 SomeIP Event Group 规则 (来自 User Chen 的修正)
```

---

## 3. 知识互惠机制

### 3.1 互惠的本质

```mermaid
flowchart TB
    subgraph "用户使用 Agent"
        USE[用户使用 Agent 完成任务]
        CORRECT[用户发现 Agent 输出有误并修正]
    end

    subgraph "修正分类"
        DETECT[检测到修正]
        CLASSIFY{分类引擎}
    end

    subgraph "写入 Agent 的 Skill"
        WRITE_L0{改 SKILL.md?<br/>工作流本身有误}
        WRITE_L1[写入 references/L1/<br/>跨模块通用知识]
        WRITE_L2[写入 references/L2/module/<br/>模块特有知识]
        WRITE_MEM[写入 Agent MEMORY.md<br/>Agent 的经验积累]
    end

    subgraph "审批"
        APPROVE_ARCH[架构师/专家审批<br/>L0 + L1 变更]
        APPROVE_MOD[模块负责人审批<br/>L2 变更]
    end

    subgraph "生效"
        ALL_BENEFIT[所有用户下次使用时<br/>Agent 已具备新知识]
    end

    USE --> CORRECT
    CORRECT --> DETECT
    DETECT --> CLASSIFY
    
    CLASSIFY -->|"工作流步骤有误"| WRITE_L0
    CLASSIFY -->|"架构/规范/通用规则"| WRITE_L1
    CLASSIFY -->|"模块特有"| WRITE_L2
    CLASSIFY -->|"Agent 应记住的经验"| WRITE_MEM
    CLASSIFY -->|"用户个人偏好"| USER_L3[写入 User L3<br/>无需审批]
    
    WRITE_L0 --> APPROVE_ARCH
    WRITE_L1 --> APPROVE_ARCH
    WRITE_L2 --> APPROVE_MOD
    WRITE_MEM --> APPROVE_MOD
    
    APPROVE_ARCH -->|通过| ALL_BENEFIT
    APPROVE_MOD -->|通过| ALL_BENEFIT
```

### 3.2 具体场景

**场景：User Chen 使用 REQ Agent 生成需求，发现 Agent 不知道 SomeIP 规则**

```mermaid
sequenceDiagram
    participant Chen as Chen (飞书)
    participant Agent as REQ Agent
    participant Plugin as OpenStar Plugin
    participant Approval as 审批服务
    participant Skill as requirement-generation/references/L1/

    Chen->>Agent: "生成 Audio 模块的接口需求"
    Agent->>Agent: 加载 SKILL.md (L0 工作流)<br/>加载 references/L1/architecture/<br/>加载 references/L2/audio/
    Agent-->>Chen: 输出: "接口使用 REST API 通信..."
    
    Chen->>Agent: "错了，我们用 SomeIP 不是 REST"
    Agent-->>Chen: "好的，已按 SomeIP 修正"
    
    Note over Agent, Plugin: Plugin 检测到修正模式

    Plugin->>Plugin: 分析修正:<br/>"REST → SomeIP" 是架构级通信规则<br/>分类: L1 (跨模块通用)
    
    Plugin->>Approval: 提交审批:<br/>修改: references/L1/architecture/communication/someip-rules.md<br/>追加规则: "接口通信必须使用 SomeIP"<br/>审批人: architect
    
    Plugin-->>Chen: "已记录。通信规则更新已提交架构团队审批。"
    
    Note over Approval, Skill: 架构师 Zhang 审批
    Approval->>Skill: 写入 someip-rules.md<br/>git commit

    Note over Chen, Skill: 此后任何用户使用 REQ Agent<br/>生成任何模块的接口需求时<br/>Agent 都会自动遵循 SomeIP 规则
```

### 3.3 写入的粒度

| 修正类型 | 写入位置 | 举例 | 审批人 |
|---|---|---|---|
| 工作流本身有误 | `SKILL.md` (L0) | "应该先检查追溯链再推送" | 架构师 |
| 架构/通信/流程规范 | `references/L1/xxx.md` | "必须用 SomeIP" | 架构师 |
| L1 依赖的子知识 | `references/L1/topic/sub-topic/` | 新增接口定义文件 | 架构师 |
| 模块特有规则 | `references/L2/module/xxx.md` | "Audio 淡出必须 300ms" | 模块负责人 |
| Agent 的经验教训 | `memories/MEMORY.md` | "DNG API 分页有 bug" | 模块负责人 |
| 用户个人偏好 | 用户自己的 L3 memory | "我喜欢批量确认" | 无需审批 |

---

## 4. Agent Memory vs User Memory

### 4.1 区分

```mermaid
graph LR
    subgraph "Agent Memory (memories/MEMORY.md)"
        AM1["DNG REST API v3 超过 100 条时需要手动分页"]
        AM2["QA 部门对 shall/should 区分极严"]
        AM3["STARC 推送后需要等 5 秒才能查询"]
        AM4["架构师 Zhang 确认: 所有接口走 SomeIP"]
    end

    subgraph "User Memory L3 (user-chen/memory.md)"
        UM1["偏好: 批量确认不逐条"]
        UM2["习惯: 先看覆盖率再看细节"]
        UM3["常用 DNG 视图: SW-Audio-View-v2"]
        UM4["回复语言: 中文"]
    end

    AM1 ---|"属于 Agent<br/>所有用户受益"| AGENT((REQ Agent))
    AM2 --- AGENT
    AM3 --- AGENT
    AM4 --- AGENT

    UM1 ---|"属于用户<br/>仅本人生效"| USER((User Chen))
    UM2 --- USER
    UM3 --- USER
    UM4 --- USER
```

### 4.2 Agent Memory 也需要审批

Agent Memory 记录的是 Agent 的**公共经验**，会影响所有用户。所以写入 Agent Memory 同样需要审批：

- Agent 自动发现的经验 → 提交审批 → 模块负责人确认 → 写入
- 用户显式告知 Agent 记住的东西 → 判断是个人偏好(L3)还是公共经验(Agent Memory) → 后者需审批

---

## 5. 系统架构

### 5.1 总体架构

```mermaid
graph TB
    subgraph "用户入口"
        FEISHU[飞书]
        WEB[Web UI]
    end

    subgraph "Enterprise Gateway (新增)"
        AUTH[认证 SSO/LDAP]
        ROUTER[路由: User → Agent]
        L3_SVC[L3 Memory 管理<br/>注入/隔离]
        APPROVAL_SVC[审批服务<br/>Skill/Memory 变更]
        AUDIT[审计日志]
    end

    subgraph "Agent Pool (Hermes Profiles)"
        subgraph "req-agent"
            REQ_SOUL[SOUL.md]
            REQ_MEM[Agent MEMORY.md]
            REQ_SKILLS[skills/<br/>requirement-generation/<br/>dng-integration/<br/>clarification-protocol/]
            REQ_RT[AIAgent Runtime]
        end
        
        subgraph "test-agent"
            TEST_SOUL[SOUL.md]
            TEST_MEM[Agent MEMORY.md]
            TEST_SKILLS[skills/<br/>test-case-generation/<br/>starc-integration/]
            TEST_RT[AIAgent Runtime]
        end
    end

    subgraph "User Memory Store"
        UM[user-chen/memory.md<br/>user-li/memory.md<br/>user-wang/memory.md]
    end

    subgraph "Orchestration"
        MASTER[Master Agent<br/>Kanban Dispatcher]
    end

    FEISHU --> AUTH
    WEB --> AUTH
    AUTH --> ROUTER
    ROUTER --> REQ_RT
    ROUTER --> TEST_RT
    L3_SVC --> UM
    L3_SVC -->|注入 system prompt| REQ_RT
    
    REQ_RT -->|修正检测| APPROVAL_SVC
    APPROVAL_SVC -->|审批通过| REQ_SKILLS
    APPROVAL_SVC -->|审批通过| REQ_MEM
    APPROVAL_SVC --> AUDIT

    MASTER --> REQ_RT
    MASTER --> TEST_RT
```

### 5.2 多用户共用 Agent — Session 隔离

```mermaid
sequenceDiagram
    participant UA as User A (Audio PO)
    participant UB as User B (ADAS PO)
    participant GW as Gateway
    participant Agent as req-agent

    Note over GW, Agent: Hermes Gateway 已有:<br/>session_key 隔离不同用户的对话历史<br/>agent_cache 复用同一 Agent 实例

    UA->>GW: "生成 Audio 需求"
    GW->>GW: session_key = feishu:chen:chat1
    GW->>Agent: 投递 (session A)
    Note over Agent: 加载 SKILL.md (L0)<br/>+ references/L1/ (全部)<br/>+ references/L2/audio/ (按模块)<br/>+ Agent Memory<br/>+ User A 的 L3 memory

    UB->>GW: "生成 ADAS 需求"
    GW->>GW: session_key = feishu:li:chat2
    GW->>Agent: 投递 (session B)
    Note over Agent: 加载 SKILL.md (L0)<br/>+ references/L1/ (全部)<br/>+ references/L2/adas/ (按模块)<br/>+ Agent Memory<br/>+ User B 的 L3 memory

    Note over UA, Agent: 共用 L0 + L1 + Agent Memory<br/>各自看到自己模块的 L2<br/>各自注入自己的 L3
```

### 5.3 references 按需加载机制

SKILL.md 中声明的工作流步骤引用 references，Agent 在执行时按需读取：

```mermaid
flowchart LR
    S1["Step 1: 确认模块"]
    S2["Step 2: 加载架构知识"]
    S3["Step 3: 生成需求"]
    S4["Step 4: 质量检查"]

    L1_ARCH["references/L1/architecture/"]
    L1_RULES["references/L1/writing-rules/"]
    L2_MOD["references/L2/module/"]
    SCRIPT["scripts/validate-requirement.py"]

    S1 --> S2
    S2 -->|读取| L1_ARCH
    S2 --> S3
    S3 -->|读取| L1_RULES
    S3 -->|读取| L2_MOD
    S3 --> S4
    S4 -->|执行| SCRIPT
```

**scripts/ 也是按需加载** — 不是所有脚本都在每次执行时运行，而是 SKILL.md 工作流中指定在特定步骤调用。

---

## 6. 技术实现

### 6.1 OpenStar Plugin (核心组件)

整个治理逻辑通过一个 Hermes Plugin 实现，零侵入内核：

```python
class OpenStarPlugin:
    """
    Hermes Plugin — 企业治理层。
    利用 Hermes 已有的 Hook 机制注入:
    1. pre_gateway_dispatch: 认证 + L3 注入 + 模块解析
    2. pre_tool_call: 拦截对 Agent Skill/Memory 的写入
    3. post_llm_call: 修正检测 + 分类
    """

    # --- 认证 + L3 注入 ---
    def pre_gateway_dispatch(self, event, gateway, session_store):
        user = self.authenticate(event.source)
        if not user:
            return {"action": "skip"}
        
        # 确定用户所属模块 → 决定加载哪个 L2
        module = user.module  # "audio" / "adas" / ...
        
        # 注入 L3 memory + 模块信息到 session context
        l3_memory = self.load_user_memory(user.id)
        event.metadata["openstar_context"] = {
            "user": user,
            "module": module,
            "l3_memory": l3_memory,
            "l2_filter": f"references/L2/{module}/"
        }
        return {"action": "allow"}

    # --- 拦截 Agent 知识写入 ---
    def pre_tool_call(self, tool_name, args, agent):
        if tool_name == "skill_manage":
            return self._gate_skill_write(args)
        if tool_name == "memory_write":
            return self._gate_agent_memory_write(args)
        return None

    def _gate_skill_write(self, args):
        path = args.get("path", "")
        
        # 写入 SKILL.md (L0) → 架构师审批
        if path.endswith("SKILL.md"):
            self.submit_approval("L0", args, approver="architect")
            return {"action": "block", "message": "L0 工作流变更已提交架构师审批"}
        
        # 写入 references/L1/ → 架构师审批
        if "/references/L1/" in path:
            self.submit_approval("L1", args, approver="architect")
            return {"action": "block", "message": "L1 知识变更已提交架构师审批"}
        
        # 写入 references/L2/ → 模块负责人审批
        if "/references/L2/" in path:
            module = self._extract_module_from_path(path)
            self.submit_approval("L2", args, approver=f"owner:{module}")
            return {"action": "block", "message": f"L2 变更已提交 {module} 负责人审批"}
        
        # scripts/ 写入 → 架构师审批 (代码变更)
        if "/scripts/" in path:
            self.submit_approval("script", args, approver="architect")
            return {"action": "block", "message": "脚本变更已提交审批"}
        
        return None

    # --- 修正检测 ---
    def post_llm_call(self, messages, response, agent):
        correction = self._detect_user_correction(messages)
        if correction:
            classification = self._classify_correction(correction)
            # classification: {level: "L1", topic: "communication", ...}
            self._submit_as_knowledge_contribution(classification, correction)
```

### 6.2 L2 模块动态过滤

**问题：** 一个 Skill 的 `references/L2/` 下有多个模块的文件夹，不同用户只应看到自己模块的。

**方案：** Plugin 在 prompt 构建时，根据用户模块过滤 L2 references 的加载。

```python
def on_skill_load(self, skill_path, agent_context):
    """Hook: Skill 加载时过滤 references/L2/"""
    module = agent_context.get("openstar_module")
    if not module:
        return  # 不过滤
    
    l2_path = skill_path / "references" / "L2"
    if l2_path.exists():
        # 只保留当前用户模块的 L2 子目录
        for subdir in l2_path.iterdir():
            if subdir.is_dir() and subdir.name != module:
                # 标记为本次 session 不加载
                agent_context.setdefault("excluded_refs", []).append(str(subdir))
```

### 6.3 审批后的写入流程

```mermaid
sequenceDiagram
    participant Approver as 审批人 (Web UI/飞书)
    participant EGL as 审批服务
    participant FS as Agent Profile 文件系统
    participant Git as Git (版本控制)

    Approver->>EGL: 批准变更 #1234
    EGL->>EGL: 验证审批权限
    
    alt 新增 reference 文件
        EGL->>FS: 写入 references/L1/xxx/new-file.md
    else 修改现有文件
        EGL->>FS: patch references/L1/xxx/existing.md
    else 修改 SKILL.md
        EGL->>FS: patch SKILL.md 中的相关步骤
    else 修改 Agent Memory
        EGL->>FS: append memories/MEMORY.md
    end
    
    EGL->>Git: git add + commit<br/>"[OpenStar] L1: 新增 SomeIP 通信规则<br/>贡献者: Chen | 审批人: Zhang"
    EGL->>EGL: 记录审计日志
    
    Note over FS, Git: 下次 Agent 加载 Skill 时<br/>自动获取最新内容
```

---

## 7. 部署方案

### 7.1 容器部署

```mermaid
graph TB
    subgraph DOCKER["Docker Compose"]
        EGL["openstar-egl\nFastAPI 认证+审批+审计"]
        PG[("PostgreSQL")]
        REQ["hermes-req-agent\nGateway + OpenStar Plugin"]
        TEST["hermes-test-agent\nGateway + OpenStar Plugin"]
        MASTER["hermes-master\nKanban Dispatcher"]
        LLM["litellm\nLLM Proxy 模型路由+配额"]
        WEB["openstar-web\nWeb UI 审批面板+控制塔"]
    end

    subgraph VOLUMES["Shared Volumes"]
        SKILLS_VOL["/skills - Git Repo\nAgent Skills 版本化"]
        USER_MEM_VOL["/user-memories\n各用户 L3"]
    end

    EGL --> PG
    REQ --> SKILLS_VOL
    TEST --> SKILLS_VOL
    REQ --> LLM
    TEST --> LLM
    EGL --> SKILLS_VOL
    WEB --> EGL
    MASTER --> REQ
    MASTER --> TEST
```

### 7.2 知识版本化

```bash
# Agent 的 skills 目录作为 Git Repo
~/.hermes/profiles/req-agent/skills/
├── .git/
├── requirement-generation/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
│       ├── L1/
│       └── L2/
└── dng-integration/
    └── ...

# 每次审批通过的变更 = 一次 git commit
# 回滚 = git revert
# 审计 = git log --all
# 知识演进可视化 = git log --graph
```

---

## 8. 对比总结

### 8.1 为什么这个结构是对的

| 原则 | 说明 |
|---|---|
| **Skill = 完整能力单元** | 一个文件夹就是一个能力，包含工作流 + 知识 + 脚本 |
| **SKILL.md = L0** | 标准工作流定义，与用户/模块无关 |
| **references/ 内分层** | L1 (通用) 和 L2 (模块) 在同一 Skill 的 references 内组织 |
| **L1 可嵌套** | `references/L1/topic/sub-topic/` 无限深度 |
| **scripts/ 按需加载** | SKILL.md 指定哪个步骤调用哪个脚本 |
| **Agent Memory 独立** | 不在 Skill 内，是 Agent 级别的经验积累 |
| **User L3 不属于 Agent** | 外部注入，不影响 Agent 的知识体系 |

### 8.2 与 Claude Agent SDK 对比

| | Hermes + OpenStar Plugin | Claude Agent SDK 从零建 |
|---|---|---|
| Skill 系统 | ✅ 原生支持完整结构 | ❌ 需自建 |
| references/ 嵌套 | ✅ 已支持 | ❌ 需设计 |
| scripts/ 执行 | ✅ 原生工具调用 | ⚠️ 需接入 |
| 多用户 Session 隔离 | ✅ Gateway ContextVar | ❌ 需实现 |
| Plugin Hook (零侵入治理) | ✅ 5 种 Hook 点 | ❌ 无此机制 |
| 飞书 Gateway | ✅ 原生适配器 | ❌ 需 2-3 周开发 |
| Kanban 编排 | ✅ SQLite CAS 跨 Profile | ❌ 需设计+实现 |
| **新增开发量** | **~10 周** (Plugin + EGL + Web UI) | **~25 周** (全部) |

---

## 9. 实施路线

| Phase | 周期 | 交付物 |
|---|---|---|
| **0: 验证** | 2 周 | 手工搭建 1 个 req-agent Profile + 飞书接入 + 2 用户验证 |
| **1: Plugin + 审批** | 4 周 | OpenStar Plugin + 审批服务 + L3 注入 + 基础 Web UI |
| **2: 修正闭环** | 3 周 | 修正检测 + LLM 分类 + 自动提交审批 + Agent Memory 积累 |
| **3: 多 Agent** | 3 周 | test-agent + quality-agent + Master Agent 编排 |

---

*End of Document v3.0*
