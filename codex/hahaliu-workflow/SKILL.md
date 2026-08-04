---
name: hahaliu-workflow
description: >-
  Codex 个人工程任务的裁决与编排层：在当前项目规则、项目级 auto-skill、Codex 原生计划/目标机制、gstack、superpowers 和子智能体之间选择唯一主链，并按 fast、focused、full、review 四条路径约束 Task Delta、Git 与发布授权、评审和当次验证证据。Use when 当前项目没有更具体的 project-auto-skill 覆盖，且用户要求实现或修复、修改行为/文案/配置、增加功能、性能优化、主动重构、代码审计、QA、发版检查、需求澄清、开工、收尾、复盘或选择工作流。位置已知且不需定位或验证的纯拼写/标点修正，以及用户已点名唯一执行 skill 或工具且无需裁决冲突时不触发；点名多个体系并要求选型时仍触发。
---

# Hahaliu Workflow

把本 skill 当作工程控制面，而不是第五套实现框架：判断任务形状，选择唯一主链，附加必要门禁与评审镜头，再用当次证据完成交付。

## 启动顺序

1. 服从用户本次明确指令和当前 system/developer 约束。
2. 从工作目录向仓库根读取适用的 `AGENTS.md`，并检查 `.agents/skills/*-auto-skill/SKILL.md`。若项目 auto-skill 明确覆盖当前任务，让它负责业务路由；本 skill 只保留授权、任务归属和新鲜证据底线。
3. 读取本任务实际要调用的其他 skill 的完整 `SKILL.md`。不要凭名字臆造能力，也不要同时启动两套负责澄清、计划、实现和完成判定的编排链。
4. 按下表定档，并先发一行：`路径: <fast|focused|full|review> | 主链: <名称> | 门禁: <清单或 none> | 验证: <关键检查>`。
5. focused/full 在实施前建立简短目标契约：目标、范围与非目标、约束、子任务、风险、验收标准。多步骤任务同步维护原生 plan；用户显式使用 `/goal` 或要求持续完成时，遵守[工作流](references/workflows.md)中的目标模式协议。
6. 只做能追溯到目标契约的最小改动。修改类任务在首次编辑前使用 Task Delta；完成前运行与风险匹配的当次验证。

## 四条路径

| 路径 | 选择条件 | 最小骨架 |
|---|---|---|
| fast | 落点和语义都明确的文档、文案或机械配置小改，不改变公共行为契约 | 定位 → 快照 → 最小修改 → 定向验证 |
| focused | 根因或需求已明确的单链 bug、小功能、局部行为改动、单模块性能优化或行为保持重构 | bug/功能走 TDD；性能/重构走专用证据循环 → 单轴 review → 定向验证 |
| full | 新能力、模糊需求、公共契约、跨层改动或高风险边界 | 澄清 → 计划/规格 → 逐切片实现 → 独立评审 → 显式验收重放 |
| review | 用户要求只审计、诊断、评估或 QA 报告，不授权修改 | 只读取证 → 分轴 findings → 标明未验证范围 → 声明未修改文件 |

以下任一条件至少升到 full：新增或修改 schema、wire format、持久化格式；触及认证、权限、密钥、数据出域或路径沙箱；同时修改两个以上独立区域；需要决定产品语义、兼容策略或不可逆迁移。项目 auto-skill 的升级清单优先。

## 唯一主链与门禁

- **主链**负责澄清、计划、实现编排和完成判定，同一任务只能有一条。
- **门禁**是在固定节点执行的检查，如复现、TDD、权限确认、完成前验证；门禁不另起编排链。
- **评审镜头**对同一任务 delta 独立检查 Standards、Spec 或安全性；保留各自结论，不把分歧平均掉。
- 根因未知时，把 `superpowers:systematic-debugging` 作为 focused 主链的诊断阶段；行为修改优先使用 `superpowers:test-driven-development`。需求、评审、QA、发版和会话技能的选择见[路由细则](references/routing.md)。
- 小任务留在主上下文顺序完成；只有独立问题域、独立文件所有权或确需上下文隔离的评审才派子智能体。派发规则见[子智能体](references/agents.md)。

## 授权与任务归属

- 未经用户本次明确授权，不执行任何改变工作树、index、本地 refs 或远端状态的 Git 写命令，也不发布、部署、发信、创建外部 issue 或触发真实业务副作用。用户只说“修复/完成/开工”不等于授权 commit、push 或发布。
- 允许实现代码时，只授权任务范围内的文件修改；不顺手清理用户既有脏树，不 stash、reset、clean 或覆盖不相关改动。
- 修改前运行 `scripts/task-delta.sh begin`，对每个将改文件先 `capture`；收尾 `render` 生成任务专属 patch。不要用 `git diff ... HEAD` 猜本任务归属。完整协议见[工作流](references/workflows.md)。
- 页面开发验收遵守当前 `AGENTS.md` 和用户指定的浏览器约束；用户要求真实 Chrome 或真实登录态时，不用内部浏览器、模拟器或其他自动化工具替代。

## 完成标准

- fast/focused：运行能覆盖本次改动风险的最小当次验证。
- full/发版/高风险：逐条重放验收标准，并执行定向测试、类型检查、构建或真实页面行为验证中的适用项。
- 区分本任务引入失败、原有失败和环境阻塞；旧测试数字、静态 validator、TODO 勾选或子智能体自报不能代替当次运行证据。
- 最终报告固定说明：用户可见结果、修改文件、实际验证命令及结果、未验证项与风险、Git/发布实际状态。有修改时明确未提交；只读任务明确未修改文件。

## 按需读取

- 路由歧义、skill 冲突和副作用边界：读 [routing.md](references/routing.md)。
- feature、bugfix、review、QA、发版和 Task Delta 完整走法：读 [workflows.md](references/workflows.md)。
- 需要派子智能体或独立评审时：读 [agents.md](references/agents.md)。
- 个性化偏好会影响路由时：读 [profile.md](references/profile.md)。当前用户指令、`AGENTS.md` 和 live 证据始终优先。
- 为项目创建 auto-skill 时：读 [project-skill-template.md](references/project-skill-template.md)。
- 修改或验证本 skill 时：读 [evaluation.md](references/evaluation.md)。

静态自检运行 `scripts/validate-workflow.sh`；脚本自测运行 `scripts/validate-workflow.sh --selftest`。静态 PASS 只证明结构与规则 lint，不证明真实路由行为；复杂修订必须按 evaluation.md 用 fresh-context 子智能体冷测。
