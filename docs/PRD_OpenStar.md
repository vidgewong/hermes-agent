# OpenStar Product Requirements Document

# OpenStar 产品需求文档

**Version / 版本:** 1.1
**Author / 作者:** Wang Yuzhi
**Date / 日期:** 2026-05-07  
**Status / 状态:** Draft / 草案

---
> 该数字员工主动参与到 RDCS 所有的工作环节，积累各项业务所需的背景知识和工程经验，最终具备独立完成各类业务需求的能力。
## 1. Executive Summary / 执行摘要

### EN

OpenStar is an enterprise-grade, multi-user, highly autonomous Digital Worker platform — essentially OpenClaw for the enterprise. It empowers MB software teams to maintain technical authority over supplier-managed development while significantly improving work efficiency. OpenStar hosts and governs specialized agents across the full ASPICE software development lifecycle (V1 focuses on Requirement Agent, Test Agent, and Quality Agent), orchestrated by Gateway + Master Agent with unified scheduling, resource management, and multi-channel interaction.

OpenStar is designed for continuous evolution — it optimizes based on user feedback and business practice, distilling domain knowledge and engineering experience into reusable digital assets that deepen its understanding and capability over time.

### CN

OpenStar 是一个面向企业级多用户的高度自主化数字员工（平台），即面向企业的 OpenClaw，赋能 RDCS 在管理供应商开发中保持技术主导权并显著提升工作效率。OpenStar 承载、治理各个专业 Agent，覆盖完整 ASPICE 软件研发全生命周期（V1 版重点支持 Requirement Agent、Test Agent 及 Quality Agent），由 Gateway + Master Agent 统一调度、管理资源，支持多端交互。

OpenStar 具备持续成长能力，能基于用户反馈与业务实践不断优化，将行业知识与工程经验沉淀为可复用的数字资产，从而增强对业务工作的理解和能力。

---

## 2. Vision & Differentiator / 愿景与差异化优势

### EN

**Vision**

OpenStar delivers highly autonomous Digital Workers to Mercedes-Benz engineering teams — AI agents that independently execute ASPICE engineering tasks across the full V-model lifecycle, continuously learn from team expertise, and operate within enterprise-grade governance. The platform transforms fragmented, manual engineering workflows into a connected, event-driven system where changes propagate automatically and knowledge compounds across teams.

**Core Differentiators**

| # | Differentiator | vs. Alternatives |
|---|---|---|
| 1 | **Highly Autonomous Execution** — agents own tasks end-to-end, operating across corporate systems (DNG, STARC, GitLab) without step-by-step human guidance | Generic AI tools require constant prompting; OpenStar agents act independently like real employees |
| 2 | **ASPICE-Native** — built for the automotive software lifecycle, not generic chat; agents natively understand ASPICE process areas, traceability chains, and QA attribute standards | No existing AI platform is designed around automotive V-model workflows; generic tools require extensive prompt engineering to produce ASPICE-compliant outputs |
| 3 | **Event-Driven Chain Reaction** — upstream changes automatically cascade impact analysis and draft updates across the entire traceability chain | Eliminates weeks-long delays in discovering downstream impact of requirement changes |
| 4 | **Compounding Intelligence** — layered knowledge architecture (L0–L4) ensures every validated correction permanently improves the system for all users | Personal assistants learn per-user only; OpenStar accumulates team-wide expertise |
| 5 | **Enterprise Governance by Design** — centralized multi-user platform with full auditability, InfoSec-compliant architecture, and architect-controlled knowledge authority | Personal AI assistants are prohibited; generic frameworks lack governance; OpenStar is both autonomous AND compliant |

### CN

**愿景**

OpenStar 为梅赛德斯-奔驰工程团队提供高度自主的数字员工——能够独立执行覆盖 V 模型全生命周期的 ASPICE 工程任务、持续从团队专业经验中学习、并在企业级治理框架内运作的 AI 智能体。平台将分散的、手动的工程工作流转变为互联的事件驱动系统，变更自动传播、知识跨团队累积。

**核心差异化优势**

| #   | 差异化优势                                                               | 对比替代方案                                              |
| --- | ------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | **高度自主执行** — 智能体端到端承担任务，跨企业系统（DNG、STARC、GitLab）独立运作，无需逐步人工指导        | 通用 AI 工具需持续提示；OpenStar 智能体像真实员工一样独立行动               |
| 2   | **ASPICE 规范** — 为汽车软件生命周期而建，非通用对话工具；智能体天然理解 ASPICE 过程域、追溯链及 QA 属性标准 | 无现有 AI 平台围绕汽车 V 模型工作流设计；通用工具需大量提示工程才能产出 ASPICE 合规产物 |
| 3   | **事件驱动全链联动** — 上游变更自动在整条追溯链上级联影响分析与更新草案                             | 消除发现需求变更下游影响所需的数周延迟                                 |
| 4   | **知识复利增长** — 分层知识架构（L0–L4）确保每次经验证的修正永久提升系统对所有用户的服务能力                | 个人助手仅单用户学习；OpenStar 积累团队级专业知识                       |
| 5   | **治理内建于架构** — 集中式多用户平台，完整审计能力，信息安全合规架构，架构师管控知识                      | 个人 AI 助手有风险；通用框架缺乏治理；OpenStar 自主又合规                 |

---

## 3. Design Principles / 设计原则

### 3.1 Core Principle / 核心原则

**EN:** A Real Team Member, Not a Tool  
**CN:** 真正的团队成员，而非工具

The Digital Worker operates like a real employee: it owns tasks end-to-end, takes initiative when it sees work to be done, learns from feedback, and accumulates expertise over time. You assign it a job — it reads from DNG, drafts requirements, pushes to STARC, monitors pipelines, and proactively alerts you when something needs attention. It doesn't wait to be asked step by step. It acts, learns, and improves autonomously within its domain of responsibility.

数字员工的行为模式与真实员工一致：它端到端承担任务、主动发现并执行待办工作、从反馈中学习，并随时间积累专业经验。你给它分配工作——它自行从 DNG 读取需求、起草软件需求、推送至 STARC、监控流水线，并在需要关注时主动提醒你。它不需要被逐步指挥，而是在其职责范围内自主行动、学习、持续进化。

### 3.2 Architectural Principles / 架构原则

| #   | Principle (EN)                                                                                                                                                                                                                                                       | 原则 (CN)                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | **Autonomous by Default:** Agents own complete workflows. They read inputs, produce outputs, push to corporate systems, and monitor results — independently. Human involvement is at review gates, not at every step.                                                | **默认自主：** 智能体拥有完整工作流。它们独立读取输入、生成输出、推送至企业系统并监控结果。人类在审阅关口介入，而非每一步都需要参与。     |
| 2   | **Platform-as-Orchestrator:** The Digital Worker is Master Agent + Gateway + Service Suite. Users interact with one "employee" — work is dispatched to domain-specific agents behind the scenes.                                                                     | **平台即编排器：** 数字员工是主智能体 + 网关 + 服务套件的组合。用户与一个"员工"交互——工作在幕后分派给领域专用智能体。        |
| 3   | **Proactive, Not Reactive:** Agents don't just respond to commands. They watch for upstream changes, detect quality issues in MRs, identify test gaps — and act on them before being asked.                                                                          | **主动而非被动：** 智能体不仅响应指令。它们监视上游变更、检测 MR 中的质量问题、识别测试空白——并在被要求之前就采取行动。         |
| 4   | **Learns Like an Employee:** Every correction compounds. The Feedback Validation Gateway classifies corrections, updates knowledge layers, and ensures the agent never makes the same mistake twice. Growth is permanent and shared.                                 | **像员工一样学习：** 每次修正都在累积。反馈验证网关分类修正、更新知识层，确保智能体不会重复同样的错误。成长是永久的且团队共享的。       |
| 5   | **Collective Intelligence, Individual Output:** One agent's learning benefits ALL future users across all modules. But specific work products stay private in the requesting user's workspace.                                                                       | **集体智慧，个体产出：** 一个智能体的学习惠及所有模块的所有未来用户。但具体工作产物仅留在请求用户的工作空间内。                |
| 6   | **Live Chain Reaction:** The full ASPICE chain is a connected, event-driven system. A change at any point cascades downstream automatically — upstream modification triggers impact analysis, draft updates, and notifications across the entire traceability chain. | **全链实时联动：** 完整 ASPICE 链是互联的事件驱动系统。任何节点的变更自动向下游级联——上游修改触发影响分析、草稿更新和全追溯链通知。 |
| 7   | **Extensible Workforce:** Adding a new agent is like hiring a new team member. It registers, gets a workspace, connects to knowledge layers, and starts contributing — no platform redesign required.                                                                | **可扩展的劳动力：** 新增一个智能体如同招聘一位新成员。它注册、获得工作空间、接入知识层并开始贡献——无需平台重构。              |

---

## 4. Project Classification / 项目分类

| Dimension / 维度         | Value / 值                                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Project Type / 项目类型    | Autonomous Digital Worker Platform / 自主数字员工平台                                                                    |
| Domain / 领域            | Automotive & Embedded Development (ASPICE) / 汽车及嵌入式开发 (ASPICE)                                                   |
| Complexity / 复杂度       | High / 高 — multi-agent governance, corporate integrations, layered knowledge architecture / 多智能体治理、企业系统集成、分层知识架构 |
| Project Context / 项目背景 | Greenfield / 全新项目 — 3 developers + 1 AI counselor + 1.5 FTE                                                      |

---

## 5. Success Criteria / 成功标准

### 5.1 User Success / 用户成功标准

| Agent / 智能体          | Criterion (EN)                                                                                                                                                             | 标准 (CN)                                                 |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| SWE.1 (Requirements) | PO provides system requirements + architecture context → Digital Worker generates complete SW requirements. 60% meet Quality Department standards without manual revision. | PO/FO 提供系统需求 + 架构上下文 → 数字员工生成完整软件需求。60% 无需人工修订即达质量部门标准。 |
| SWE.6 (Test)         | When SW requirements become available, agent auto-iterates test cases and pushes to STARC. 60% directly usable.                                                            | 软件需求就绪后，智能体自动迭代测试用例并推送至 STARC。60% 可直接使用。                |
| Quality Agent        | Proactively identifies code quality issues across MRs and notifies responsible person. V1 focuses on detection and notification.                                           | 主动识别 MR 中的代码质量问题并通知责任人。V1 聚焦检测与通知。                      |
| Growth Signal        | Acceptance rate climbs steadily over time as agent learning compounds through user corrections.                                                                            | 随着用户修正的累积学习，接受率随时间稳步攀升。                                 |

### 5.2 Business Success / 商业成功标准

| Timeframe / 时间节点  | Target (EN)                                                              | 目标 (CN)                               |
| ----------------- | ------------------------------------------------------------------------ | ------------------------------------- |
| Week 12–15        | Internal beta release; SWE.1 + SWE.6 operational for at least one module | 内部 Beta 发布；SWE.1 + SWE.6 至少在一个模块中投入运行 |
| Beta success gate | 60% of generated requirements pass standards without revision            | 60% 生成的需求无需修订即通过标准                    |
| Week 16+          | Onboard additional modules; demonstrate cross-module improvement         | 接入更多模块；展示跨模块改进效果                      |
| 6-month horizon   | Multiple project teams actively using the platform                       | 多个项目团队（Civic, Adas）活跃使用平台             |

### 5.3 Technical Success / 技术成功标准

| Criterion (EN)                                                                                 | 标准 (CN)                                         |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Single MB server deployment stable under multi-user load                                       | 单台奔驰服务器部署在多用户负载下稳定运行                            |
| End-to-end traceability chain operational: System Req (DNG) → SW Req (DNG) → Test Case (STARC) | 端到端追溯链运行：系统需求 (DNG) → 软件需求 (DNG) → 测试用例 (STARC) |
| Feedback Validation Gateway correctly classifying corrections                                  | 反馈验证网关正确分类用户修正                                  |
| Agent decision audit trail complete and inspectable via Web UI                                 | 智能体决策审计轨迹完整且可通过 Web UI 查阅                       |
| Event-driven cascading functional                                                              | 事件驱动级联功能正常运作                                    |

### 5.4 Measurable Outcomes / 可量化指标

| Metric (EN)         | 指标 (CN) | Target / 目标                                                     |
| ------------------- | ------- | --------------------------------------------------------------- |
| Acceptance rate     | 接受率     | 60% at beta, growing over time / Beta 阶段 60%，持续增长               |
| Growth rate         | 增长率     | Week-over-week improvement per module / 逐周逐模块改善                 |
| Coverage            | 覆盖率     | Number of modules with active engagement / 活跃模块数量               |
| Time savings        | 时间节省    | Reduction in PO effort for requirements drafting / PO 需求编写工作量减少 |
| Proactive detection | 主动检测    | Quality issues caught before human discovery / 人工发现前捕获的质量问题数    |

---

## 6. User Journeys / 用户旅程

### 6.1 Module PO — Requirements Generation (Primary) / 模块 PO — 需求生成

**EN:** Chen, PO for the Infotainment Audio module, receives a notification that the system team has released new system requirements. He needs to decompose **32** system requirements into software requirements—a task that previously required **2–3 days** of manual analysis. Chen tells **OpenStar** via Feishu: "Generate software requirements for the new system requirements." The **Requirement Agent** resolves the DNG address from the **L1** knowledge layer, ingests the system requirements, cross-references architecture knowledge and reference documents, and maintains continuous communication with Chen to refine the requirements. Once the software requirements are pushed to DNG, the Digital Worker notifies Chen: "**48** software requirements generated and pushed to DNG." Chen finds **30 of the 48** requirements immediately acceptable and corrects the remaining **18** in DNG. The agent detects these corrections and updates the module-specific memory (**L2**).

Weeks later, the module undergoes **18 system requirement changes** (including 10 new and 8 updated requirements). OpenStar generates the software requirements again and notifies Chen. This time, Chen finds that **16 of the 18** generated software requirements are directly usable, with only **2** requiring minor corrections.

The acceptance rate has climbed from **60% to 90%**.

**CN:** Chen 是信息娱乐音频模块的 PO，系统团队发布新系统需求后，OpenStar抓住 hook 事件并主动通过 feishu/teams 告知 Chen。他需要将 32 条系统需求分解为软件需求——以前需要 2–3 时间进行需求分析。Chen 通过飞书告诉 OpenStar ："为新系统需求生成软件需求。" Requirement Agent 从 L1 知识层解析 DNG 地址，摄取系统需求，交叉引用架构知识和参考文档，并和 Chen 持续沟通需求，完成软件需求。在数字员工推送软件需求到 DNG 后，主动通知 Chen："已生成 48 条软件需求并推送至 DNG。" Chen 发现 48 条中有 30 条直接可用，在 DNG 中修正了其余 18 条。Agent 检测到修正，并更新模块专属记忆（L2）。

数周后，该模块的系统需求发生了 18 条系统需求变更，包括新增10条，更新原有的8条，OpenStar 再次生成并迭代软件需求并通知 Chen，Chen 发现生成的 18 条软件需求有 16 条可以直接使用，仅需修正其余 2 条需求。

接受率从 60% 攀升至 90%。

### 6.2 Module PO — First Interaction (Onboarding) / 模块 PO — 首次交互（引导）

**EN:** Li, PO for a new module, tells the Digital Worker to generate requirements. The agent has no L1 context yet — it asks: "Which software requirement specification do you need to update? Could you provide the link?" Li provides the DNG link. The agent stores this as module context and proceeds. Initial output quality is ~50%. Through several correction cycles, the agent rapidly builds L2 knowledge and matches the 60% threshold within 2–3 iterations.

**CN:** Li 是新模块的 PO，告诉数字员工生成需求。智能体尚无 L1 上下文——询问："需要更新哪份软件需求规格？请提供链接。" Li 提供 DNG 链接。智能体将其存储为模块上下文并开始工作。初始输出质量约 50%。经过几轮修正循环，智能体快速构建 L2 知识，在 2–3 次迭代内达到 60% 阈值。

### 6.3 Tech Lead (TL) — Oversight & Escalation / 技术领导 (TL) — 监督与升级

**EN:** Wang, engineering manager overseeing 4 module teams, receives a Feishu alert about systemic interface definition issues detected across 3 modules. He opens the Web UI control tower, reviews the Quality Agent's analysis with evidence from 12 MRs, initiates dialogue with the Digital Worker, and instructs the architect to update L1 knowledge. Once updated, all modules benefit immediately.

**CN:** Wang 是负责 4 个模块团队的工程经理，收到飞书告警：3 个模块中检测到系统性接口定义问题。他打开 Web UI 控制塔，审阅质量智能体基于 12 个 MR 的分析证据，与数字员工对话，并指示架构师更新 L1 知识。更新完成后，所有模块立即受益。

### 6.4 Architect — L1 Knowledge Governance / 架构师 — L1 知识治理

**EN:** Zhang, software architect, reviews 3 L1 candidate corrections flagged by the Feedback Validation Gateway. Through the Web UI knowledge management interface, he approves one (traceability attribute format), rejects one (too module-specific, reclassifies as L2), and defers one pending further evidence. The approved change propagates immediately to all agents across all modules.

**CN:** Zhang 是软件架构师，审阅反馈验证网关标记的 3 条 L1 候选修正。通过 Web UI 知识管理界面，他批准一条（追溯属性格式标准化），拒绝一条（过于模块化，重分类为 L2），搁置一条等待更多证据。获批的变更立即传播至所有模块的所有智能体。

### 6.5 CI/CD Team — Test Injection Approval / CI/CD 团队 — 测试注入审批

**EN:** A developer on the Infotainment module submits a Merge Request implementing a new audio fade-out feature. Upon MR creation, the CI/CD server triggers OpenStar's SWE.6 Agent via webhook. The agent analyzes the MR diff, identifies which software requirements are touched, retrieves the corresponding test cases from STARC, and dynamically generates a verification test job. This job is injected into the GitLab pipeline (pending CI/CD team approval). The pipeline executes — the test job fails, reporting that the fade-out duration does not meet the expected 500ms threshold.

The developer reviews the failure and disagrees: the implementation correctly uses a 300ms fade-out as specified in the latest system requirement update (which superseded the old 500ms spec). The developer raises feedback through Feishu: "The test is wrong — requirement SR-4821 was updated to 300ms fade-out." The SWE.6 Agent receives this feedback, cross-references the current requirement in DNG, confirms the developer is correct, and updates its module-specific knowledge (L2) — recording that SR-4821 now specifies 300ms. The agent also regenerates the affected test case in STARC and updates the test script template.

Two weeks later, another developer submits an MR touching the same audio fade-out logic. The SWE.6 Agent generates the verification job with the correct 300ms threshold. The test passes. The acceptance rate for auto-generated test jobs in this module climbs from 70% to 85%.

**CN:** 信息娱乐模块的一名开发者提交了一个实现音频淡出功能的 Merge Request。MR 创建时，CI/CD 服务器通过 Webhook 触发 OpenStar 的 Test Agent。Test Agent 分析 MR diff，识别涉及的软件需求，从 STARC 检索对应的测试用例，并动态生成验证测试 Job。该 Job 被注入 GitLab 流水线（需 CI/CD 团队审批）。流水线执行后，测试 Job 失败，报告淡出时长不满足预期的 500ms 阈值。

开发者审查失败结果后表示不认同：实现中正确使用了 300ms 淡出时长，这是最新系统需求更新的规格（取代了旧的 500ms 规格）。开发者通过飞书反馈："测试有误——需求 SR-4821 已更新为 300ms 淡出。" SWE.6 智能体接收到反馈后，交叉引用 DNG 中的当前需求，确认开发者是正确的，并更新其模块专属知识（L2）——记录 SR-4821 现在规定 300ms。智能体同时重新生成 STARC 中受影响的测试用例并更新测试脚本模板。

两周后，另一名开发者提交了涉及同一音频淡出逻辑的 MR。SWE.6 智能体使用正确的 300ms 阈值生成验证 Job。测试通过。该模块自动生成测试 Job 的接受率从 70% 攀升至 85%。

### Journey Capabilities Summary / 旅程能力矩阵

| Journey / 旅程 | Capabilities (EN) | 能力 (CN) |
|---|---|---|
| PO - Happy Path | Feishu NL command, DNG integration (R/W), requirements generation, notification, L1 context resolution | 飞书自然语言指令、DNG 集成（读/写）、需求生成、通知、L1 上下文解析 |
| PO - Onboarding | Clarification protocol, DNG link registration, progressive learning, L2 bootstrapping | 澄清协议、DNG 链接注册、渐进学习、L2 知识引导 |
| Tech Lead (TL) | Web UI control tower, cross-module analytics, systemic pattern detection, Feishu alerting | Web UI 控制塔、跨模块分析、系统性模式检测、飞书告警 |
| Architect | Web UI knowledge management, L1 approval workflow, Feedback Gateway review, cross-module propagation | Web UI 知识管理、L1 审批流程、反馈网关审核、跨模块传播 |
| CI/CD Team | MR-triggered test job generation, pipeline injection with approval gates, developer feedback loop, automated knowledge update (L2), test case regeneration | MR 触发测试 Job 生成、流水线注入审批关口、开发者反馈闭环、自动知识更新（L2）、测试用例重新生成 |

---

## 7. Domain-Specific Requirements / 领域特定需求

### 7.1 Process Compliance (ASPICE) / 流程合规 (ASPICE)

| Requirement (EN) | 需求 (CN) |
|---|---|
| Agent outputs structurally compatible with ASPICE process areas (SWE.1, SWE.6, SYS.2, SYS.5) | 智能体输出结构上兼容 ASPICE 过程域 (SWE.1, SWE.6, SYS.2, SYS.5) |
| Quality standards are internal MB QA requirements, not external regulatory standards | 质量标准为奔驰内部 QA 要求，非外部法规标准 |
| Dedicated agent skills handle Quality Department formatting and attribute compliance | 专用智能体技能处理质量部门格式化及属性合规 |
| Suboptimal initial generation acceptable — manual editing to meet QA standards is expected | 初始生成不完美是可接受的——人工编辑达标是预期内的工作流程 |

### 7.2 Integration Constraints / 集成约束

| Constraint (EN)                                                                            | 约束 (CN)                        |
| ------------------------------------------------------------------------------------------ | ------------------------------ |
| SSO/LDAP required for all corporate system integrations                                    | 所有企业系统集成必须使用 SSO/LDAP 认证       |
| API rate limits exist on corporate platforms — agents must implement rate-aware scheduling | 企业平台存在 API 速率限制——智能体须实现速率感知调度  |
| ~~HiAgent provides MCP servers as standardized integration layer~~                         | ~~HiAgent 提供 MCP 服务器作为标准化集成层~~ |

### 7.3 Risk Mitigation / 风险缓解

| Boundary (EN) | 边界 (CN)                                                                | Governance / 治理      |
| ------------- | ---------------------------------------------------------------------- | -------------------- |
| DNG           | Requirements are drafts until PO reviews and approves baseline         | 需求为草稿状态直至 PO 审阅并批准基线 |
| STARC         | Test cases require human review before becoming effective              | 测试用例须经人工审阅方可生效       |
| CI/CD         | Test injection requires team approval; rollback is recommendation-only | 测试注入需团队审批；回滚仅为建议     |

**Conclusion / 结论:** The platform's governance model (human approval gates at every output boundary) makes catastrophic agent failure a quality issue, not a safety issue.

平台治理模型（每个输出边界均设人工审批关口）使智能体灾难性失败成为质量问题而非安全问题。

---

## 8. Technical Architecture / 技术架构

### 8.1 Deployment / 部署

| Aspect (EN) | 方面 (CN) | Description / 描述 |
|---|---|---|
| Container topology | 容器拓扑 | Single container (Backend + Master Agent + internal services + internal agents); external agents in separate containers / 单容器（后端 + 主智能体 + 内部服务 + 内部智能体）；外部智能体独立容器 |
| Hot-reload | 热更新 | Supported — no platform restart for agent updates / 支持——智能体更新无需平台重启 |
| Health checks | 健康检查 | Backend performs health checks on all agents / 后端对所有智能体执行健康检查 |
| Versioning | 版本控制 | Agents independently versionable; zero-downtime updates / 智能体独立版本化；零停机更新 |

### 8.2 Multi-Agent Communication / 多智能体通信

| Aspect (EN)       | 方面 (CN) | Description / 描述                                                                                              |
| ----------------- | ------- | ------------------------------------------------------------------------------------------------------------- |
| Protocol          | 协议      | A2A or ACP、http 等，外部 agent 统一封装成 MCP                                                                          |
| Topology          | 拓扑      | Agents can invoke other agents directly (no mandatory Master Agent routing) / 智能体可直接调用其他智能体（无需强制经过主智能体路由）     |
| Master Agent role | 主智能体角色  | Orchestration, conflict detection, resource governance — not a communication bottleneck / 编排、冲突检测、资源治理——非通信瓶颈 |

### 8.3 Knowledge Persistence Layer / 知识持久化层 (Per Agent)

| Layer / 层级 | Scope (EN)                                                          | 范围 (CN)             | Croos-User | Authority / 权限                                |
| ---------- | ------------------------------------------------------------------- | ------------------- | ---------- | --------------------------------------------- |
| L0         | Base capabilities — shared, immutable                               | 基础能力——共享、不可变        | Yes        | Platform config / 平台配置                        |
| L1         | Team/Project knowledge — cross-module                               | 团队/项目知识——跨模块        | Yes        | Architect write-only / 仅架构师可写                 |
| L2         | Module-specific — per workspace, supports cross-module querying     | 模块专属——按工作空间，支持跨模块查询 | Yes        | PO corrections / PO 修正                        |
| L3         | User-personal — individual habits, preferences, behavioral patterns | 用户个人——个人习惯、偏好、行为模式  | No         | Accumulated from user interactions / 从用户交互中积累 |
| L4         | Session context — ephemeral                                         | 会话上下文——临时性          | No         | No persistence / 无持久化                         |

### 8.4 User Isolation / 用户隔离

| Level (EN)     | 级别 (CN) | Description / 描述                                                                                                                         |
| -------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Process-level  | 进程级     | Independent agent instances per user / 每用户独立智能体实例                                                                                        |
| Database-level | 数据库级    | Separate schemas per user / 每用户独立 Schema                                                                                                 |
| Dual workspace | 双工作空间   | Shared intelligence (L0–L2) across users; personal knowledge (L3) + work products isolated per user / 共享智能（L0–L2）跨用户；个人知识（L3）+ 工作产物按用户隔离 |

### 8.5 LLM Routing / 大模型路由

| Aspect (EN)    | 方面 (CN) | Description / 描述                                                             |
| -------------- | ------- | ---------------------------------------------------------------------------- |
| Infrastructure | 基础设施    | LiteLLM provides unified LLM API suite / LiteLLM 提供统一大模型 API 套件              |
| Configuration  | 配置      | Web UI allows per-agent LLM API configuration / Web UI 允许按智能体配置大模型 API       |
| Flexibility    | 灵活性     | Each agent can use a different model suited to its task / 每个智能体可使用适合其任务的不同模型 |
|                |         |                                                                              |

---

## 9. Phased Development / 分阶段开发

### 9.1 MVP Strategy / MVP 策略

**EN:** End-to-end workflow MVP — prove the entire ASPICE chain works from natural language command through to published artifacts in corporate systems (DNG, STARC). Two agents (SWE.1 + SWE.6) demonstrate the full platform value proposition.

**CN:** 端到端工作流 MVP——验证从自然语言指令到企业系统（DNG, STARC）发布产出物的完整 ASPICE 链路。两个智能体（REQ + TEST）支持积累知识。

**Core Principle / 核心原则:** The MVP is not a demo — it must bridge real workflows. Generated requirements must land in DNG; generated test cases must land in STARC. Without these integrations, the platform delivers no measurable value.

MVP 不是演示——必须对接真实工作流。生成的需求必须落地 DNG；生成的测试用例必须落地 STARC。没有这些集成，平台无法交付可衡量的价值。

### 9.2 Phase 1 — Beta (Week 12–15) / 第一阶段 — Beta（第 12–15 周）

| Capability (EN)                  | 能力 (CN)                | Rationale / 理由                                                                                    |
| -------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------- |
| SWE.1 Agent (Requirements)       | SWE.1 智能体（需求）          | Core value proposition / 核心价值主张                                                                   |
| SWE.6 Agent (Test/Qualification) | SWE.6 智能体（测试/验证）       | Completes the ASPICE chain / 闭合 ASPICE 链路                                                         |
| DNG MCP Integration (R/W)        | DNG MCP 集成（读/写）        | Without DNG push, no workflow value / 无 DNG 推送则无工作流价值                                             |
| STARC MCP Integration (write)    | STARC MCP 集成（写）        | Without STARC push, test cases don't enter real workflow / 无 STARC 推送则测试用例无法进入真实流程                |
| Feishu/HiAgent integration       | 飞书/HiAgent 集成          | Primary interaction channel / 主要交互通道                                                              |
| Web UI (observation + audit)     | Web UI（观测 + 审计）        | Activity monitoring and decision auditability / 活动监控与决策可审计性                                       |
| Knowledge layers L0–L3           | 知识层 L0–L3              | Agent growth mechanism (shared + personal) — required for 60% target / 智能体成长机制（共享 + 个人）——60% 目标所需 |
| Feedback Validation Gateway      | 反馈验证网关                 | Drives agent improvement / 驱动智能体改进                                                                |
| Backend (health, hot-reload)     | 后端（健康检查、热更新）           | Agent lifecycle management / 智能体生命周期管理                                                            |
| Master Agent (orchestration)     | 主智能体（编排）               | Coordination without conflicts / 无冲突协调                                                            |
| A2A protocol (async)             | A2A 协议（异步）             | Agent-to-agent communication / 智能体间通信                                                             |
| User isolation (process + DB)    | 用户隔离（进程 + 数据库）         | Multi-user from day one / 第一天起支持多用户                                                               |
| LiteLLM + Web UI LLM config      | LiteLLM + Web UI 大模型配置 | Per-agent model configuration / 按智能体配置模型                                                          |
| Full decision audit trail        | 完整决策审计轨迹               | Every agent action logged / 每个智能体动作均有记录                                                           |

### 9.3 Phase 2 — Growth / 第二阶段 — 增长

| Feature (EN)                         | 功能 (CN)     | Dependency / 依赖                                             |
| ------------------------------------ | ----------- | ----------------------------------------------------------- |
| Quality Agent (proactive monitoring) | 质量智能体（主动监控） | L2 cross-module querying operational / L2 跨模块查询就绪           |
| CronJob engine                       | 定时任务引擎      | Quality Agent's primary trigger / 质量智能体主要触发机制               |
| Natural language CronJob definition  | 自然语言定时任务定义  | Users describe intent → platform translates / 用户描述意图 → 平台翻译 |
| Daily summary & reporting            | 日报与报表生成     | Role-based from Jira/GitLab/DNG/STARC / 基于角色从各系统生成          |
| Event-driven upstream reaction       | 事件驱动上游响应    | Stable DNG integration from MVP / 依赖 MVP 中稳定的 DNG 集成        |
| Multi-module deployment              | 多模块部署       | Proven single-module success / 单模块验证成功                      |
| CLI for power users                  | 命令行工具（高级用户） | Terminal-native workflow integration / 终端原生工作流集成            |
| Escalation timers                    | 升级计时器       | Unacknowledged → escalate after threshold / 未确认 → 超时后升级     |
| Systemic pattern detection           | 系统性模式检测     | Cross-MR/developer analysis / 跨 MR/开发者分析                    |
| Attention budget management          | 注意力预算管理     | Per-agent, per-user notification limits / 按智能体、按用户通知上限      |

### 9.4 Phase 3 — Vision / 第三阶段 — 愿景

| Feature (EN)                          | 功能 (CN)           |
| ------------------------------------- | ----------------- |
| SYS.2 Agent (system requirements)     | SYS.2 智能体（系统需求）   |
| SYS.5 Agent (system integration test) | SYS.5 智能体（系统集成测试） |
| Autonomous task execution             | 自主任务执行            |
| Coding Agent, Bug Management Agent    | 编码智能体、缺陷管理智能体     |
| Teams/email channel expansion         | Teams/邮件通道扩展      |
| Mobile access                         | 移动端接入             |
| Semantic consistency checking         | 语义一致性检查           |

---

## 10. Functional Requirements / 功能需求

### 10.1 Requirement Agent / 需求 Agent

| ID   | Requirement (EN)                                                                                                                                  | 需求 (CN)                                              |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| FR1  | MB worker can instruct the Digital Worker via natural language to generate SW requirements from system requirements                               | MB 员工可通过自然语言指示数字员工从系统需求生成软件需求                        |
| FR2  | SWE.1 Agent can ingest system requirements from DNG and cross-reference architecture knowledge and reference code                                 | SWE.1 智能体可从 DNG 摄取系统需求，并交叉引用架构知识与参考代码                |
| FR3  | SWE.1 Agent can generate complete SW requirements with traceability attributes, verification criteria, and interface specs                        | SWE.1 智能体可生成完整软件需求（含追溯属性、验证准则、接口规格）                  |
| FR4  | SWE.1 Agent can push generated requirements directly to DNG as draft artifacts                                                                    | SWE.1 智能体可将生成的需求作为草稿直接推送至 DNG                        |
| FR5  | SWE.1 Agent can detect user corrections in DNG and capture those corrections                                                                      | SWE.1 智能体可检测用户在 DNG 中的修正并捕获                          |
| FR6  | SWE.1 Agent can resolve context (DNG address) from L1 knowledge without asking the user                                                           | SWE.1 智能体可从 L1 知识解析上下文（DNG 地址）而无需询问用户                |
| FR7  | SWE.1 Agent can ask clarifying questions when required context is unavailable (hallucination-aware clarification protocol)                        | SWE.1 智能体在缺少必要上下文时可主动澄清（幻觉感知的澄清协议）                   |
| FR8  | SWE.1 Agent can notify PO upon completion with summary of updated requirements                                                                    | SWE.1 智能体可在完成后通知 PO 并附已更新需求摘要                        |
| FR9  | SWE.1 Agent can use reference code as read-only context with strict hierarchy: new system requirements > architectural knowledge > reference code | SWE.1 智能体可将参考代码作为只读上下文使用，严格遵循优先级：新系统需求 > 架构知识 > 参考代码 |
| FR10 | SWE.1 Agent can flag conflicts between reference code and new system requirements                                                                 | SWE.1 智能体可标记参考代码与新系统需求之间的冲突                          |

### 10.2 Event-Driven Reactions (SWE.1) / 事件驱动响应 (SWE.1)

| ID   | Requirement (EN)                                                                    | 需求 (CN)                                 |
| ---- | ----------------------------------------------------------------------------------- | --------------------------------------- |
| FR11 | SWE.1 Agent can detect upstream system requirement changes in DNG via event/webhook | SWE.1 智能体可通过事件/Webhook 检测 DNG 中上游系统需求变更 |
| FR12 | SWE.1 Agent can identify impacted downstream SW requirements                        | SWE.1 智能体可识别受影响的下游软件需求                  |
| FR13 | SWE.1 Agent can draft updates to impacted requirements and notify PO for review     | SWE.1 智能体可起草受影响需求的更新并通知 PO 审阅           |

### 10.3 Test & Qualification (SWE.6 Agent) / 测试与验证 (SWE.6 智能体)

| ID   | Requirement (EN)                                                                                                                                              | 需求 (CN)                                               |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| FR14 | SWE.6 Agent can generate qualification test cases from approved SW requirements and architecture documents                                                    | SWE.6 智能体可从已批准的软件需求和架构文档生成验证测试用例                      |
| FR15 | SWE.6 Agent can push generated test cases directly to STARC                                                                                                   | SWE.6 智能体可将生成的测试用例直接推送至 STARC                         |
| FR16 | SWE.6 Agent can iterate test cases through user review cycles (continuous bidirectional iteration)                                                            | SWE.6 智能体可通过用户审阅循环迭代测试用例（持续双向迭代）                      |
| FR17 | SWE.6 Agent can determine automation feasibility per test case (virtualizable vs. requires hardware)                                                          | SWE.6 智能体可判定每个测试用例的自动化可行性（可虚拟化 vs. 需硬件）               |
| FR18 | SWE.6 Agent can generate executable test scripts in two stages: (1) test cases defining what to verify, (2) framework-specific scripts defining how to verify | SWE.6 智能体可分两阶段生成可执行测试脚本：(1) 测试用例定义验证什么 (2) 框架脚本定义如何验证 |
| FR19 | SWE.6 Agent can recommend test injection for specific MRs to CI/CD team                                                                                       | SWE.6 智能体可向 CI/CD 团队推荐为特定 MR 注入测试 job                 |
| FR20 | SWE.6 Agent can automatically update affected test cases when upstream requirements change                                                                    | SWE.6 智能体可在上游需求变更时自动更新受影响的测试用例                        |

### 10.4 CI/CD Integration / CI/CD 集成

| ID   | Requirement (EN)                                                                                            | 需求 (CN)                               |
| ---- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| FR22 | Platform can dynamically compose test jobs based on requirements touched by an MR                           | 平台可根据 MR 涉及的需求动态组合测试任务                |
| FR23 | CI/CD team can approve or reject test injection recommendations (never auto-injects)                        | CI/CD 团队可批准或拒绝测试注入建议（绝不自动注入）          |
| FR24 | ~~Quality Agent can recommend rollback when CI failure traced to faulty test script (recommendation only)~~ | ~~质量智能体可在 CI 失败追溯至测试脚本错误时建议回滚（仅为建议）~~ |

### 10.5 Knowledge Architecture & Agent Growth / 知识架构与智能体成长

| ID   | Requirement (EN)                                                                                                                               | 需求 (CN)                             |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| FR31 | Platform maintains layered knowledge store (L0–L4) with distinct access/write authorities                                                      | 平台维护分层知识存储（L0–L4），各层具有不同的访问/写入权限    |
| FR32 | Feedback Validation Gateway classifies corrections as: universal rule, module-specific preference, one-time exception, or incorrect correction | 反馈验证网关将修正分类为：通用规则、模块特定偏好、一次性例外或错误修正 |
| FR33 | Platform loads knowledge progressively per task (only relevant module context loaded)                                                          | 平台按任务渐进加载知识（仅加载相关模块上下文）             |
| FR34 | Platform performs load-time consistency checks between L1 and L2, warning of conflicts and halting for resolution                              | 平台在加载时执行 L1/L2 一致性检查，冲突时告警并暂停等待解决   |
| FR35 | Architect can review and approve/reject pending L1 knowledge proposals via Web UI                                                              | 架构师可通过 Web UI 审阅并批准/拒绝待处理的 L1 知识提案  |
| FR36 | Validated feedback propagates to benefit all future users of the same agent                                                                    | 经验证的反馈传播以惠及同一智能体的所有未来用户             |
| FR37 | Platform accumulates behavioral memory per module owner — agent instances diverge through usage                                                | 平台按模块负责人积累行为记忆——智能体实例通过使用产生分化       |
| FR38 | Process/methodology feedback always classified as L1 — requires architect approval                                                             | 流程/方法论反馈始终归类为 L1——需架构师批准            |
| FR39 | Platform surfaces supporting data to architects but never proposes or auto-promotes to L1                                                      | 平台向架构师呈现支撑数据但绝不主动提议或自动提升至 L1        |

### 10.6 Platform Governance & Orchestration / 平台治理与编排

| ID   | Requirement (EN)                                                                                                                                                                                | 需求 (CN)                                                    |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| FR40 | Master Agent detects conflicting operations on shared artifacts and sequences them                                                                                                              | 主智能体检测共享产物上的冲突操作并排序执行                                      |
| FR41 | Master Agent manages resource budgets (tokens, API calls, attention, concurrency) via unified governance                                                                                        | 主智能体通过统一治理管理资源预算（Token、API 调用、注意力、并发）                      |
| FR42 | Agents can autonomously publish draft artifacts to corporate systems (e.g., draft requirements to DNG, draft test cases to STARC), but approval/baseline operations require human authorization | 智能体可自主向企业系统发布草案产物（如草案需求至 DNG、草案测试用例至 STARC），但审批/基线操作须经人工授权 |
| FR43 | Platform enforces human approval gates at baseline and release boundaries — agents cannot approve, merge, or promote artifacts to official status                                               | 平台在基线与发布边界强制执行人工审批关口——智能体不能审批、合并或将产物提升为正式状态                |
| FR44 | Backend performs health checks on all agents                                                                                                                                                    | 后端对所有智能体执行健康检查                                             |
| FR45 | Backend supports hot-reload without platform restart                                                                                                                                            | 后端支持热更新无需平台重启                                              |
| FR46 | Master Agent's arbitration engine is registrable, adjustable, business-agnostic, and decoupled                                                                                                  | 主智能体仲裁引擎可注册、可调节、业务无关、解耦                                    |
| FR47 | Platform manages attention budgets — per-agent, per-user notification limits with overflow batched into digests                                                                                 | 平台管理注意力预算——按智能体、按用户设通知上限，溢出部分批量汇总                          |

### 10.7 Proactive & Scheduled Operations / 主动与定时操作

| ID   | Requirement (EN)                                                                                                       | 需求 (CN)                             |
| ---- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| FR48 | Quality Agent executes agent-owned CronJobs with defined scope, data sources, output format, and notification channels | 质量智能体执行其拥有的定时任务（定义范围、数据源、输出格式、通知通道） |
| FR49 | Users can define CronJobs in natural language — platform translates to scheduled task                                  | 用户可用自然语言定义定时任务——平台翻译为调度任务           |
| FR50 | CronJobs fork from standard templates into per-module sub-tasks at execution time                                      | 定时任务从标准模板在执行时派生为按模块子任务              |
| FR51 | Quality Agent generates configurable role-based daily/weekly summaries                                                 | 质量智能体生成可配置的基于角色的日报/周报               |
| FR52 | Quality Agent proactively detects code vulnerabilities in MRs/Jira                                                     | 质量智能体主动检测 MR/Jira 中的代码漏洞            |
| FR53 | Quality Agent detects systemic patterns across MRs/developers and escalates with evidence                              | 质量智能体检测跨 MR/开发者的系统性模式并附证据升级         |
| FR54 | Platform supports configurable escalation timers for unacknowledged notifications                                      | 平台支持可配置的升级计时器处理未确认通知                |

### 10.8 Multi-Agent Communication / 多智能体通信

| ID   | Requirement (EN)                                                                                       | 需求 (CN)                             |
| ---- | ------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| FR55 | Agents communicate asynchronously via A2A protocol                                                     | 智能体通过 A2A 协议异步通信                    |
| FR56 | Agents can invoke other agents directly without mandatory Master Agent routing                         | 智能体可直接调用其他智能体而无需强制经过主智能体路由          |
| FR57 | Platform supports agent discovery and capability negotiation                                           | 平台支持智能体发现与能力协商                      |
| FR58 | SWE.1 can hand off completed requirements to SWE.6 for automatic test case generation                  | SWE.1 可将完成的需求移交 SWE.6 以自动生成测试用例     |
| FR59 | Agent addition is first-class — new agents register, get workspace, connect to feedback/audit pipeline | 平台原生支持智能体扩展——新增智能体通过标准注册流程即可自动获得独立工作空间、接入知识层及反馈/审计管线，无需定制开发 |

### 10.9 User Interaction — Feishu/HiAgent / 用户交互 — 飞书/HiAgent

| ID   | Requirement (EN)                                         | 需求 (CN)            |
| ---- | -------------------------------------------------------- | ------------------ |
| FR60 | Users issue natural language commands via Feishu         | 用户通过飞书发出自然语言指令     |
| FR61 | Digital Worker sends structured notifications via Feishu | 数字员工通过飞书发送结构化通知    |
| FR62 | Platform routes user replies to correct agent session    | 平台将用户回复路由至正确的智能体会话 |
| FR63 | Tech leads (TL) receive escalation alerts via Feishu     | 技术领导 (TL) 通过飞书接收升级告警    |
| FR64 | Users receive configurable summaries via Feishu          | 用户通过飞书接收可配置的摘要报告   |

### 10.10 User Interaction — Web UI / 用户交互 — Web UI

| ID   | Requirement (EN)                                                                      | 需求 (CN)                  |
| ---- | ------------------------------------------------------------------------------------- | ------------------------ |
| FR65 | Users observe real-time agent activity in Web UI                                      | 用户在 Web UI 中观察实时智能体活动    |
| FR66 | Users browse historical workspace artifacts and past iterations                       | 用户浏览历史工作空间产物和过往迭代        |
| FR67 | Users engage in direct dialogue with Digital Worker through Web UI                    | 用户通过 Web UI 与数字员工直接对话    |
| FR68 | Administrators view control tower of all agent activities                             | 管理员查看所有智能体活动的控制塔视图       |
| FR69 | Architect manages L1 knowledge through Web UI only                                    | 架构师仅通过 Web UI 管理 L1 知识   |
| FR70 | Users configure LLM API assignments per agent                                         | 用户按智能体配置大模型 API 分配       |
| FR71 | Standard users see only their triggered activities; administrators have control tower | 普通用户仅见自己触发的活动；管理员拥有控制塔视图 |

### 10.11 User Interaction — CLI / 用户交互 — CLI

| ID   | Requirement (EN)                                                                               | 需求 (CN)              |
| ---- | ---------------------------------------------------------------------------------------------- | -------------------- |
| FR72 | Developers invoke agent tasks via CLI (e.g., `dw run swe6 --req SW-REQ-4721 --generate-tests`) | 开发者通过 CLI 调用智能体任务    |
| FR73 | CLI supports scripting and terminal-native workflow integration                                | CLI 支持脚本编写与终端原生工作流集成 |

### 10.12 User Management & Isolation / 用户管理与隔离

| ID   | Requirement (EN)                                               | 需求 (CN)                |
| ---- | -------------------------------------------------------------- | ---------------------- |
| FR74 | Independent agent instances per user (process isolation)       | 每用户独立智能体实例（进程隔离）       |
| FR75 | Separate database schemas per user (data isolation)            | 每用户独立数据库 Schema（数据隔离）  |
| FR76 | Share agent intelligence (L0–L2) across users; isolate personal knowledge (L3) and work products per user | 跨用户共享智能体智能（L0–L2）；按用户隔离个人知识（L3）及工作产物 |
| FR77 | Backend manages user provisioning and lifecycle              | 后端管理用户配置与生命周期          |

### 10.13 Auditability & Traceability / 可审计性与追溯性

| ID   | Requirement (EN)                                                                              | 需求 (CN)                                    |
| ---- | --------------------------------------------------------------------------------------------- | ------------------------------------------ |
| FR78 | Every agent decision logged as immutable event (what was seen, decided, why, context, output) | 每个智能体决策记录为不可变事件（所见、所决、原因、上下文、输出）           |
| FR79 | Agent decision history viewable as timeline in Web UI (time-travel debugging)                 | 智能体决策历史可在 Web UI 中以时间轴查看（时间旅行调试）           |
| FR80 | Intermediate artifacts persisted for multi-step workflows (each stage inspectable)            | 多步骤工作流中间产物持久化（每阶段可检视）                      |
| FR81 | End-to-end traceability: System Req → SW Req → Test Case → Test Script → Pipeline → Verdict   | 端到端追溯：系统需求 → 软件需求 → 测试用例 → 测试脚本 → 流水线 → 裁定 |
| FR82 | Configurable logging verbosity per trigger mode (user-triggered: full; CronJob: summary)      | 按触发模式配置日志详细度（用户触发：完整；定时任务：摘要）              |
| FR83 | Time-windowed retention (full detail for configurable window, compressed summary for archive) | 时间窗口保留策略（配置窗口内完整详情，归档为压缩摘要）                |

---

## 11. Non-Functional Requirements / 非功能性需求

### 11.1 Performance / 性能

| Requirement (EN)                                                            | 需求 (CN)                      |
| --------------------------------------------------------------------------- | ---------------------------- |
| Agent task completion within 1 hour maximum regardless of input volume      | 智能体任务完成时间不超过 1 小时（不论输入量）     |
| User-facing interactions respond within 5 seconds to acknowledge receipt    | 面向用户的交互 5 秒内确认接收             |
| Agent progress observable in real-time via Web UI during long-running tasks | 长时运行任务期间智能体进度可通过 Web UI 实时观察 |
| Platform must not add significant overhead beyond LLM inference time        | 平台不应在大模型推理时间之外增加显著开销         |

### 11.2 Security / 安全

| Requirement (EN)                                                                                                                                                                                          | 需求 (CN)                                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **Primary:** Prevent leakage of sensitive data — no data/artifacts uploaded to external internet platforms except authorized API calls                                                                    | 防止敏感数据泄露——除授权 API 调用外，不向外部互联网平台上传数据/产物                     |
| Digital Worker operates with full privileges within its container, but all tools, services, and network access are provisioned and controlled by MB infrastructure — no unauthorized operations permitted | 数字员工在容器内拥有完全操作权限，但容器内的工具、服务及网络资源均由 MB 基础设施统一构建与管控，不允许未授权操作 |
| All corporate system integrations authenticate via SSO/LDAP                                                                                                                                               | 所有企业系统集成通过 SSO/LDAP 认证 (鉴权)                                |
| Agent audit trail must be tamper-resistant (append-only)                                                                                                                                                  | 智能体审计轨迹须防篡改（仅追加）                                           |
| User isolation prevents cross-user data leakage of work products                                                                                                                                          | 用户隔离防止工作产物跨用户泄露                                            |

### 11.3 Reliability / 可靠性

| Scenario (EN) | 场景 (CN) | Behavior / 行为 |
|---|---|---|
| DNG API unavailable | DNG API 不可用 | Generate CSV fallback + notify user / 生成 CSV 备用文件 + 通知用户 |
| STARC API unavailable | STARC API 不可用 | Generate Markdown/CSV fallback + notify / 生成 Markdown/CSV 备用 + 通知 |
| Agent failure during task | 智能体执行中失败 | Intermediate artifacts preserved; user can resume/restart / 中间产物保留；用户可恢复/重启 |
| Platform restart | 平台重启 | Recover all persistent state (knowledge, audit logs, artifacts) / 恢复所有持久化状态 |
| Target availability | 目标可用性 | Available during MB working hours; maintenance outside hours / 工作时间可用；非工作时间维护 |

### 11.4 Integration / 集成

| Requirement (EN) | 需求 (CN) |
|---|---|
| All corporate integrations use SSO/LDAP credentials | 所有企业集成使用 SSO/LDAP 凭据 |
| Respect API rate limits; implement request queuing and backoff | 遵守 API 速率限制；实现请求队列与退避策略 |
| HiAgent MCP servers as standardized integration layer | HiAgent MCP 服务器为标准化集成层 |
| When integration unavailable, produce local artifacts + notify — never block silently | 集成不可用时生成本地产物 + 通知——绝不静默阻塞 |
| Handle corporate API version changes gracefully via hot-reload | 通过热更新优雅处理企业 API 版本变更 |

### 11.5 Scalability / 可扩展性

| Requirement (EN)                                                                                | 需求 (CN)                      |
| ----------------------------------------------------------------------------------------------- | ---------------------------- |
| Initial: Support 2 project teams with concurrent users on single server                         | 初始：单服务器支持 2 个项目团队并发用户        |
| Growth: Adding teams without platform redesign                                                  | 增长：新增团队无需平台重新设计              |
| Agent scaling: Process isolation → adding users adds instances; server resources are constraint | 智能体扩展：进程隔离 → 新用户新实例；服务器资源为约束 |
| Knowledge scaling: L2 cross-module querying must remain performant as module count grows        | 知识扩展：L2 跨模块查询在模块数增长时须保持高效    |

---

## 12. Innovation

### 12.1 Innovation Areas / 创新领域

| Innovation (EN)                                     | 创新 (CN)              | Significance / 意义                                                                                                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Automated ASPICE Traceability                       | ASPICE 全链路自动化追溯      | Eliminates the need for manual maintenance of tedious traceability matrices by automatically linking system requirements, software requirements, and test cases. Any change at any stage triggers automated synchronization and alerts across the entire chain, ensuring the development process remains fully compliant with industry standards./无需人工维护繁琐的追溯表，系统自动联动系统需求、软件需求到测试用例。任一环发生变更，全链条自动同步提醒，确保研发过程始终符合合规标准。 |
| Layered Knowledge (L0–L4) with Expert-Defined Rules | 分层知识体系 (L0–L4) 与专家把控 | Enterprise-grade knowledge governance as differentiator / 企业级知识治理作为差异化优势                                                                                                                                                                                                                                                                                                                                              |
| Dual workspace model                                | 双工作空间模型              | Multi-user AI sharing without data leakage / 多用户 AI 共享而无数据泄露                                                                                                                                                                                                                                                                                                                                                          |
| Platform-as-compliance                              | 平台即合规                | InfoSec + Quality guaranteed by architecture / 信息安全 + 质量由架构保障                                                                                                                                                                                                                                                                                                                                                         |
| ~~Decoupled arbitration engine~~                    | ~~解耦仲裁引擎~~           | ~~New agents auto-extend arbitration without code changes / 新智能体自动扩展仲裁无需改代码~~                                                                                                                                                                                                                                                                                                                                         |
| Attention budget management                         | 注意力预算管理              | Prevents notification fatigue; overflow batched / 防止通知疲劳；溢出批量处理                                                                                                                                                                                                                                                                                                                                                       |

### 12.2 Market Context / 市场背景

| Competitor Type (EN)                        | 竞品类型 (CN) | Gap / 缺口                                                                                                  |
| ------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------- |
| Generic frameworks (MAF, LangGraph, CrewAI) | 通用框架      | No multi-user governance, no ASPICE, no enterprise knowledge architecture / 无多用户治理、无 ASPICE、无企业知识架构       |
| Personal assistants                         | 个人助手      | No team-level governance; improvements per-user, not shared / 无团队级治理；改进仅个人化                               |
| Enterprise AI platforms (Dify, etc.)        | 企业 AI 平台  | Lack deep agent autonomy, governance layers, domain-specific process compliance / 缺乏深度智能体自主性、治理层、领域特定流程合规 |

**Gap Conclusion / 缺口结论:** No product combines autonomous multi-agent orchestration + enterprise knowledge governance + ASPICE process compliance + multi-user isolation.

无现有产品兼具自主多智能体编排 + 企业知识治理 + ASPICE 流程合规 + 多用户隔离。

---

## 13. Risk Management / 风险管理

### 13.1 Technical Risks / 技术风险

| Risk (EN)                   | 风险 (CN)    | Impact / 影响                                | Mitigation / 缓解                                                                             |
| --------------------------- | ---------- | ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| DNG integration unreliable  | DNG 集成不稳定  | MVP delivers zero value / MVP 无价值交付        | Prototype first (Week 1–2); fallback to CSV export / 优先原型验证；备用 CSV 导出                       |
| STARC integration fails     | STARC 集成失败 | SWE.6 cannot close loop / SWE.6 无法闭环       | Early prototype; fallback to Markdown export / 早期原型；备用 Markdown 导出                          |
| 60% acceptance not achieved | 60% 接受率未达标 | Platform perceived as not useful / 平台被认为无用 | Seed L1 with architect input; accept iterative improvement / 用架构师输入预置 L1；接受迭代改进             |
| Knowledge layer conflicts   | 知识层冲突      | Agent behavior inconsistent / 智能体行为不一致     | Load-time consistency check; architect authority; halt on conflict / 加载时一致性检查；架构师最终权威；冲突时暂停 |
| Multi-user data leakage   | 多用户数据泄露    | Security incident / 安全事件                   | Dual workspace; intelligence shared, products isolated / 双工作空间；智能共享，产物隔离                    |
| Framework selection wrong   | 框架选择失误     | Rework required / 需返工                      | Platform layer framework-agnostic; agent loop swappable / 平台层框架无关；智能体循环可替换                  |

### 13.2 Resource Risks / 资源风险

| Risk (EN) | 风险 (CN) | Mitigation / 缓解 |
|---|---|---|
| Small team (3 dev + 1.5 FTE) | 小团队 | Single-container minimizes DevOps; hot-reload enables rapid iteration / 单容器最小化运维；热更新支持快速迭代 |
| Resources constrained | 资源受限 | Defer SWE.6; ship SWE.1 + DNG alone as minimum proof / 推迟 SWE.6；仅交付 SWE.1 + DNG 作为最小验证 |

### 13.3 Adoption Risk / 采纳风险

| Risk (EN) | 风险 (CN) | Mitigation / 缓解 |
|---|---|---|
| Internal product — no market pressure | 内部产品——无市场压力 | Start with one champion PO; demonstrate growth curve organically / 从一位核心 PO 开始；有机展示增长曲线 |

---

## 14. Glossary / 术语表

| Term (EN)                   | 术语 (CN)    | Definition / 定义                                                                                                                                                                    |
| --------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent                       | 智能体        | An autonomous AI entity with specific domain capabilities, operating within governance constraints / 具有特定领域能力的自主 AI 实体，在治理约束下运行                                                    |
| Digital Worker              | 数字员工       | The user-facing abstraction: Master Agent + Gateway + Service Suite / 面向用户的抽象：主智能体 + 网关 + 服务套件的组合体                                                                                 |
| Master Agent                | 主智能体       | Orchestrates work, manages resources, detects conflicts — not a communication bottleneck / 编排工作、管理资源、检测冲突——非通信瓶颈                                                                   |
| A2A                         | A2A 协议     | Agent-to-Agent asynchronous communication protocol / 智能体间异步通信协议                                                                                                                    |
| ASPICE                      | ASPICE     | Automotive SPICE — process assessment model for automotive software development / 汽车 SPICE——汽车软件开发过程评估模型                                                                           |
| DNG                         | DNG        | IBM DOORS Next Generation — requirements management tool / IBM DOORS Next Generation——需求管理工具                                                                                       |
| STARC                       | STARC      | Test case management system / 测试用例管理系统                                                                                                                                             |
| MCP                         | MCP        | Model Context Protocol — standardized integration layer / 模型上下文协议——标准化集成层                                                                                                          |
| L0–L4                       | L0–L4 知识层  | Layered knowledge architecture: L0 immutable base, L1 team knowledge, L2 module-specific, L3 user-personal, L4 ephemeral session / 分层知识架构：L0 不可变基础、L1 团队知识、L2 模块专属、L3 用户个人、L4 临时会话 |
| Feedback Validation Gateway | 反馈验证网关     | Classifies user corrections to determine scope of agent learning / 分类用户修正以确定智能体学习范围                                                                                                |
| PO                          | PO (产品负责人) | Product Owner — module-level technical authority / 产品负责人——模块级技术权威                                                                                                                  |
| CronJob                     | 定时任务       | Agent-owned scheduled task with defined scope and routing / 智能体拥有的定时任务（定义范围与路由）                                                                                                    |
| Hot-reload                  | 热更新        | Agent update without platform restart / 无需平台重启的智能体更新                                                                                                                               |
| HiAgent                     | HiAgent    | Internal Mercedes-Benz AI tool platform providing MCP servers / 奔驰内部 AI 工具平台（提供 MCP 服务器）                                                                                           |
| Attention Budget            | 注意力预算      | Per-agent, per-user notification limit to prevent fatigue / 按智能体、按用户的通知限额以防疲劳                                                                                                      |

---
End.
