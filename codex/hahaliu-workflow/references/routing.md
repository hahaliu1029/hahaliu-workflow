# 路由细则与冲突裁决

## 分层

按以下优先级裁决：用户本次指令 → system/developer 与适用 `AGENTS.md` → 项目 `.agents/skills/*-auto-skill` → hahaliu-workflow → leaf skill 自身默认。

项目 auto-skill 只在其 description 和正文明确覆盖当前任务时接管。它没有自动继承全局 skill，因此必须自带四条不变量：用户指令优先、唯一主链、未经本次授权不做副作用、完成声明引用当次证据。

## 任务入口

| 用户目标 | 默认主链 | 边界 |
|---|---|---|
| 判断问题是否值得做 | 轻量使用 `office-hours` 的问题验证方法 | 完整 gstack 流程会写持久档案；未授权时只在对话中应用方法 |
| 需求含真实产品分叉或不可逆选择 | `brainstorming` | 一次只澄清一个关键问题；获得设计认可后再实现 |
| 需求明确、只差实施 | 原生 plan + focused/full 执行 | 不为单会话小改创建规格工程 |
| 根因未知的 bug | `superpowers:systematic-debugging` | 先复现和定位根因，不猜修复 |
| 根因已知的 bug | focused + `superpowers:test-driven-development` | 先有能失败的回归证据，再最小修复 |
| 性能优化 | focused：锁定指标与负载 → 可重复基线 → profile → 单变量修改 → 同条件复测 → 功能回归 | 指标未定、涉及产品取舍、跨前后端/存储/部署层或改公共契约时升 full；只分析不修改走 review |
| 主动重构（行为保持） | focused：冻结外部行为 → characterization/GREEN 基线 → 小步等价变换 → 每步复跑 | 跨多个独立区域、修改公共 API/schema/持久化格式或架构迁移时升 full；行为变化拆成独立 feature/bug 任务 |
| 只读代码审计 | review；必要时 `deep-review` 或独立子智能体 | 不修改，不把风格偏好当 bug，findings 按严重度与证据排序 |
| 页面行为 QA | review 或 focused；直接用 `chrome:control-chrome` | 生产/未知环境中的提交、删除、支付、发信等动作先获授权 |
| 发版准备度 | review，读取并应用检查清单 | `ship`、`land-and-deploy` 含 Git/发布副作用，不进入默认路径 |
| 保存/恢复/复盘 | `context-save`、`context-restore`、`retro` | 这些 skill 可能写仓库外状态；先服从当前授权边界 |

只在 skill 实际可用且任务匹配时调用。加载前读完整 `SKILL.md`，核对它的隐式写入、Git、浏览器、外部服务和用户确认协议。如果 leaf skill 与上层授权冲突，保留方法、禁用冲突动作，并在开工行说明适配；不要假称已完整执行该 skill。

性能和重构场景不把 profiler、optimizer、架构检查或 reviewer 升格为第二条主链；它们只能提供诊断输入或评审镜头。诊断派发默认只读并显式禁止改文件；授权其实现时仍须先建立 Task Delta、限定文件所有权并按同一指标或行为不变量验收。完整调用若会压测外部系统、打开 GUI、写报告或改项目文档，必须先取得对应副作用授权。

## 需求成熟度

full 路径只选一条澄清链：

1. 需求已明确且无产品决策：说明跳过澄清，直接计划。
2. 只剩 2–3 个清晰方案：使用 `brainstorming` 做取舍。
3. 一句话需求：先调查能从仓库和当前环境查到的事实，再只向用户询问会改变产品结果的决策；以共同理解回执收口。
4. 任务巨大到一个上下文看不清：先产出假设、边界、风险与分阶段计划；不要直接实施所有内容。

共同理解回执至少包含 Outcome、User、Success evidence、Binding constraint、Out of scope、Unresolved decisions。未决产品决策会实质改变结果时，先请用户确认；纯实现细节在授权范围内采用最小可逆方案并记录假设。

## 第二次门禁

澄清完成后再按规模和副作用水位选择出口：

| 形状 | 出口 |
|---|---|
| 只要讨论结论 | 在对话中交付，到此为止 |
| 单会话可完成 | focused；维护短 plan，不创建 spec/tickets |
| 多会话、跨团队或需持久规格 | full；创建用户已授权的本地工件，按垂直切片推进 |

副作用水位不自动升级：只讨论 → 可写临时文件 → 可写工作区文件 → 可写外部系统 → 可 Git 写/发布。每次跨级都需要本次明确授权。

## 评审轴

- 无正式 spec：做 Standards/correctness 单轴评审，只看任务专属 delta。
- 有 spec 或 ticket：把 Standards 与 Spec compliance 分成两个上下文隔离的镜头。
- 认证、权限、输入解析、路径和数据出域：追加安全镜头。
- 需要独立第二意见时，优先 fresh-context 子智能体；只给原始 artifact、目标契约和边界，不泄漏预期 finding。
- 主上下文验真并综合。子智能体结论是输入，不是裁决。

## Git 与外部副作用

以下动作只在用户本次逐项授权后执行：Git add/commit/stash/switch/merge/rebase/reset/clean/fetch/pull/push、创建或更新 PR、发布部署、写外部 tracker、发信通知、修改生产数据。即使某个 skill 把它们当默认完成协议，也不能借调用 skill 隐式扩大授权。

只读 Git 命令也应限定范围并避免泄露敏感内容。`git status`、`git diff --no-index`、`git log`、`git show`、`git check-ignore` 可用于调查；不要把整棵脏工作树当成本任务成果。

## 路由例子

- “把这处已定位错别字改掉，不必测试” → 不触发本 skill。
- “修复登录偶发 500，原因未知” → focused，systematic-debugging → 回归测试 → 最小修复。
- “把明确负载下的接口延迟优化回目标值，行为不变” → focused，基线 → profile → 同条件复测 → 功能回归。
- “重构单模块但不改 API 和行为” → focused，GREEN/characterization → 小步等价变换 → 每步回归。
- “给事件协议增加字段并兼容旧客户端” → full，先冻结 wire contract 和兼容语义。
- “只审计这段权限代码，不要改” → review，安全镜头，声明未修改文件。
- “检查本地页面交互是否真的可用” → review/focused，按是否授权修复区分，真实 Chrome 验证。
- “用 gstack 和 superpowers 帮我选一套流程” → 触发本 skill，选唯一主链而非叠加。
- “使用 `$skill-creator` 创建 skill” → 已点名唯一执行 skill，本 skill 让位。

## 红旗

- 同时运行两套澄清/计划/实现编排。
- 简单修复强上完整规格流程，或高风险改动因行数少而跳过门禁。
- 未读 skill 正文就按名字猜行为。
- 用 HEAD、整个 working tree 或旧 commit 归因当前任务。
- 以 validator PASS、测试曾经通过或子智能体自报代替当次证据。
- 借 ship、QA 或 worktree 流程取得用户未授予的 Git/发布权限。
