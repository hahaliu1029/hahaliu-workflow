---
name: hahaliu-workflow
description: 工程工作流的裁决与编排层。前置：项目级 auto-skill 已覆盖当前任务时,本 skill 不触发、直接让位。Use when 非平凡任务需要在可用的原生能力、gstack、superpowers、mattpocock、ecc 之间选唯一主链,定 fast/focused/full/review 路径,安排子代理与模型档位,或用户说「开工/收尾/复盘/怎么安排/用哪个 skill」时。以下任务无论多小、需求多明确都触发：修 bug、改行为/文案/配置、加功能、性能优化、主动重构、代码审计、QA、发版检查、需求澄清(验证点子值不值得做、压测方案、一句话需求、多方案选型)——都需要本层定档与交付纪律。仅两类不触发：①位置已知的拼写/标点级修正——需定位、需测试、或改行为/文案/配置的不属此类;②用户已点名唯一的 skill/工具作为执行路径(含只问如何调用 Codex)——点名多个工具或需裁决工具间冲突属于选型,照常触发。
---

# hahaliu-workflow — 工程工作流裁决层

不是第五套流程框架,而是四套体系之上的轻量控制面: 判断任务形状→选唯一主链→附门禁与评审镜头→按分级验证→干净收尾。

## 路由优先级

1. 用户本次明确指令
2. 当前项目适用的 `<project>-auto-skill`
3. 本 skill 的默认裁决
4. 各体系自身默认流程

宿主提供的技能发现机制不参与主链竞争。当前 CLAUDE.md、项目规则和用户本次指令是持续约束；本 skill 自带公共安全底线，不依赖额外的本机 rules 文件才能工作。

**Git 底线**: 未经本次明确授权,本 skill、其子代理及被调用流程不得执行任何改变工作树、index、本地 refs 或远端状态的 git 写命令,也不得发布;尤其不得让 ship/land-and-deploy 隐式扩大授权。用户本机存在更严格规则时,叠加执行更严格约束。

## 选路(开局 30 秒定档)

| 路径 | 适用 | 骨架 |
|---|---|---|
| fast | 文档/文案/机械配置/明确不改行为契约的局部小改 | 定位→最小修改→定向验证 |
| focused | 根因或需求已明的单链 bug、小功能、单模块性能优化或行为保持重构 | bug/功能走 systematic-debugging/TDD;性能/重构分别走 Playbook H/I 专用循环→review→验证 |
| full | 新能力/模糊需求/公共契约/跨层/高风险边界 | 澄清(目标定位+成熟度门禁)→计划或 spec+tickets(大型任务加 Spec 收敛门禁)→逐票 TDD→review+镜头→显式验证门禁 |
| review | 只审计不修改 | 只读取证→分轴结论→标明未验证范围 |

review 轴数与路径无关,统一按「唯一主链」表判: 无正式 spec/ticket→Standards 单轴;有且非平凡→Standards+Spec 双轴;高风险**另加**安全/codex 镜头(镜头不改变 Spec 轴的有无)。

升级到 full 的通用触发: 新增/修改 schema、wire format、持久化格式;触及认证/密钥/数据出域/路径沙箱;同时改 2 个以上区域;需要决定产品语义或兼容策略。项目 auto-skill 的升级清单优先于此表。

触发下限(fast 不是死档): 「任务很小不触发」仅指零定位成本、零纪律增量的单点修正(如改一处拼写,直接改完验证即可);仍需要定位落点、Task Delta 快照或未提交声明纪律的局部小改属 fast,照常触发。

开工只报一行: `路径: <…> | 主链: <…> | 门禁: <…> | 验证: <关键命令>`,然后直接干(存在真实产品取舍或缺权限才停)。

focused/full 路径在开工行之后立一份**目标契约**(数行即可,不另开文档;full 已有 spec/plan 时由其承担,不重复): 目标 / 范围与非目标 / 约束 / 子任务 / 风险 / 验收标准。中途目标要变时,先显式更新契约并说明原因,再继续——不允许悄悄漂移。

## auto 模式(无人值守)

公共权威协议在 [workflows.md](references/workflows.md)「auto 模式协议」：显式进入、授权信封、硬停与执行预算、跨模型出域、恢复胶囊与自动 compact。项目 auto-skill 接管路由、或本 skill 让位时,该覆盖层依然生效,任何主链不得吞掉或放松它。本机存在更严格的 auto 规则时叠加执行。

- 澄清链自答嵌入: grill/office-hours/brainstorming 的提问改为跨模型自答(答者非主链模型,出域规则见覆盖层),结论过主链裁决入假设台账;选哪条澄清链的裁决逻辑不变(routing.md)。
- wayfinder 级的模糊大任务不适用 auto——只产出假设清单+计划+风险声明后停,不盲跑。
- 完成底线与验证纪律不因 auto 松动;台账格式、跨模型执行顺序、熔断与收尾报告模板见 [workflows.md](references/workflows.md)「auto 模式协议」。

## 唯一主链

一个任务只有一条主链(负责澄清/计划/实现编排/完成判定);验证、安全检查、codex challenge 只能作为门禁或评审镜头附着,不得开成第二条链。gstack 与 superpowers 的编排协议(AskUserQuestion 决策卡 / ExitPlanMode)不得嵌套混用。

启动时先探测下表涉及的可选集成。存在就按其真实规则调用；不存在或不可读时,用 Claude Code 原生计划、子代理、实现和评审能力完成等价最小流程,并在开工行或报告中注明 fallback。不得臆造未安装的 skill 已被调用。

默认速查(细则、例外与协议见 references/routing.md):

| 场景 | 默认 |
|---|---|
| 需求澄清 | 先定用户目标: 还在验证「值不值得做」→gstack office-hours(替代 grill,不连跑);已决定做→按成熟度门禁四档选一: 已明确→直接计划;2-3 清晰方案→brainstorming;一句话需求→MP grill 系(共同理解回执收口);看不清路线→MP wayfinder(细则见 routing.md) |
| 计划 | superpowers:writing-plans;grill 后先过第二次门禁(规模×副作用授权,routing.md)再定出口,多会话/需持久工件才 MP to-spec/to-tickets |
| 根因未知 debug | superpowers:systematic-debugging |
| TDD | superpowers:test-driven-development |
| review | 无 spec 单轴 Standards;有 spec 双轴(MP);高风险+codex 镜头 |
| 性能优化 | focused 起步;完成证据=可重复的修改前后指标(Playbook H,升级条件见 routing.md) |
| 主动重构 | focused 起步;完成证据=外部行为不变(Playbook I,升级条件见 routing.md) |
| session 存取 | gstack context-save / context-restore |
| 复盘 | gstack retro |
| 调研 | MP research |

## 完成底线

- fast/focused: 跑与风险匹配的最小当次验证。
- full/发版/高风险: 显式过 superpowers:verification-before-completion;全量矩阵才用 ecc verification-loop。
- 验证翻出的失败**必须三分类**再处置: **本任务引入**→继续修复或标记 BLOCKED,不得声称完成、不得当「遗留」交付;**原有失败**→记录 baseline 证据,不顺手修;**环境阻塞**→写明未验证范围与复现条件。收尾场景同样适用(细则见 workflows.md Playbook G-6)。
- 任何完成声明必须引用当次命令输出;报告末尾按实际情况声明——有文件修改: 报告实际提交状态(未提交明确声明;经本次授权完成的 commit 逐条列出);只读任务: 明确本次未修改文件。

## References(按需读,不预载)

- 路由歧义、跨体系冲突、codex 咨询协议、MP disable-model-invocation 技能加载 → [routing.md](references/routing.md)
- 已定任务类型,要完整走法(feature/bugfix/接手新项目/发版/收尾/节律表) → [workflows.md](references/workflows.md)
- 确实要派子代理(选型/档位/并行规则/prompt 检查单) → [agents.md](references/agents.md)
- 个性化信号影响路由时(公共版本默认中立,本地覆盖不提交;项目事实在项目 auto-skill) → [profile.md](references/profile.md)
- 仅在为项目创建 auto-skill 时 → [project-skill-template.md](references/project-skill-template.md)
- 改本 skill、跑评测/评分/轨迹审计时 → [evaluation.md](references/evaluation.md)

自检(只读): `scripts/validate-workflow.sh`(结构档,可附项目路径;`--selftest` 全量 fixture)。改本 skill 必跑 gate 冷测——三阶段冷测、评分器语义、轨迹事件审计与执行档 runner、联读审计、指标与信任边界的完整协议见 [evaluation.md](references/evaluation.md),评测细节以该文件为准。
