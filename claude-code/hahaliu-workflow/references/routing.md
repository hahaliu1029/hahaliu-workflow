# 路由细则与冲突裁决

## 分层(谁管什么)

using-superpowers 发现技能 → 项目 auto-skill 决定本项目怎么做 → hahaliu-workflow 在无项目覆盖时裁决 → leaf skill 执行。

- superpowers:using-superpowers 是技能发现协议,不参与主链竞争。
- 当前用户指令、CLAUDE.md、项目规则与跨项目记忆是持续约束,不因选了哪条链而失效。本 skill 的公共安全底线自包含；本机更严格规则只会收紧,不能放松它。

## 术语与硬规则: 主链 / 门禁 / 评审镜头

- **主链**: 负责需求澄清、计划生成、实现编排、完成判定的那条流程。一个任务只能有一条。
- **门禁**: 在固定节点必须通过的检查(如完成前验证),附着在主链上,不开新流程。
- **评审镜头**: 对同一 delta 的独立视角(Standards 轴 / Spec 轴 / 安全 / codex challenge),上下文隔离、结论并列,不合并稀释。

硬规则:

1. 不得同时运行两套负责澄清/计划/TDD 编排/完成判定的 orchestration;gstack 的 AskUserQuestion 决策卡/ExitPlanMode 协议与 superpowers 的编排协议不得嵌套。
2. leaf skill 可以被主链调用,但不能反客为主重启全流程。
3. 豁免某个门禁必须显式说一句理由,不静默跳过。

## 场景默认裁决

| 场景 | 默认 | 何时换/升级 |
|---|---|---|
| 需求澄清 | 先过下节「用户目标定位」,再按「需求成熟度门禁」四档选**唯一**澄清链 | office-hours/brainstorming/grilling/wayfinder 是同一职责的替代关系,不叠加连跑两轮访谈 |
| 规划 | 澄清完成(或需求本就明确)→writing-plans(fast 可不写正式 plan) | 跨会话/需持久规格与票→MP to-spec+to-tickets;grill 后不默认续任何链,先过「第二次门禁」(见下)再定出口;高风险架构或点名要多视角→gstack autoplan / plan-*-review |
| debug(根因未知) | superpowers:systematic-debugging | 诊断需形成可交接的持久工件→MP diagnosing-bugs(主链替代,不叠加);线上事故/运行态调查且确需 freeze/learnings→gstack investigate |
| debug(根因已知) | focused 路径直接修 | 仍必须先复现、后验证 |
| 性能优化 | focused: 锁定指标与负载→建立基线→profile 定位→单变量最小改动→同条件复测→功能回归(Playbook H) | 指标未定、涉及产品取舍、跨前后端/存储/部署层、或改公共契约/架构→full;只要求分析报告不改代码→review |
| 主动重构(行为保持) | focused: 冻结外部行为→characterization/GREEN 基线→小步等价变换→每步复跑→delta review(Playbook I) | 跨多个独立区域、改公共 API/schema/持久化格式、架构迁移或无法单会话闭环→full;重构中需要改行为→拆成独立 feature/bug 任务,不混入本 delta |
| TDD | superpowers:test-driven-development(先 RED 后 GREEN) | 测试落点(seam)拿不准时参考 MP tdd 的 seam 规则;文档/机械配置不伪造 TDD |
| review(无正式 spec) | 单轴 Standards/correctness 评审,只看任务 delta | — |
| review(有 spec/ticket 且非平凡) | MP code-review 双轴: Standards 轴+Spec 轴上下文隔离并行 | 高风险再加 codex challenge 镜头 |
| 发版准备度 | 只读档: 读取并应用 gstack review 的检查清单,**不调用完整 /review**(它会 `git fetch` 改 remote-tracking refs,Fix-First 直接改文件并持久化;其 preamble 即写 ~/.gstack 档案,首次运行的 routing 注入还会创建 CLAUDE.md 并 commit——「只跑 preamble」也不只读) | 用户同时授权「允许修改」与必要 git 更新时才跑完整 /review;ship / land-and-deploy 见「副作用边界」 |
| QA/页面行为 | 只读档: 读取并应用 gstack qa 的检查方法(逐项点按/填表/状态覆盖+结构化报告),用 claude-in-chrome 直接控制 Chrome 执行;只报不修同理,仅输出 findings。**先识别环境**——生产或未知环境里,提交/删除/支付/发信/通知等会改真实业务数据或触达外部的动作,须在执行前取得用户明确授权,不因「QA 要点全」而默认点下去 | 完整 /qa 要求干净工作树、让用户 commit/stash 且逐修 atomic commit,且首次运行的 routing 注入/测试框架 bootstrap 也会 commit(与是否发现 bug 无关);/qa 与 /qa-only 都用 gstack browse 而非 Chrome——仅当用户明确授权这些 git 动作并同意用 browse 时才整套调用;视觉走 design-review 检查清单(其 Fix 行为需修改授权) |
| 调研外部事实 | MP research(一手来源,每条 claim 标来源,落盘;只讨论/未授权写文件的会话降级为结论进对话,不落仓库) | 问题可分解为多个独立域的体系化调研→并行分域+主上下文综合(Playbook F 第二档) |
| 术语/架构决策记录 | MP domain-modeling(CONTEXT.md;ADR 三条件同时满足才写) | — |
| session 保存/恢复 | gstack context-save / context-restore(单轨) | ecc save-session 仅作 fallback,不常规并用 |
| 每周复盘 | gstack retro | 跨项目汇总用 retro global |
| 完成声明 | 恒守验证原则(分级见 SKILL.md) | 需要全量矩阵才用 ecc verification-loop,不每次叠加 |

性能/重构场景不把 MP improve-codebase-architecture、ecc performance-optimizer 或任何 reviewer 升格为主链,只作诊断输入或评审镜头。两者都不是天然只读: ecc performance-optimizer 可用时,诊断派发词须显式限定只读、禁改文件;授权其实现时先过 Task Delta 与文件所有权。MP improve-codebase-architecture 完整调用会写临时报告、打开 GUI、进入交互并可能更新项目文档,默认只读取并应用其架构评审准则;完整调用需另获对应副作用授权。集成不存在时使用 Claude Code 原生 profiling、实现与评审能力,不得伪装已调用。

## 用户目标定位(澄清的第 0 步,先于成熟度定档)

成熟度四档回答「需求有多清楚」,但更前置的问题是「用户在解决什么」——是在验证问题本身值不值得做,还是已决定做、只差把需求说清。先按目标入表,再进成熟度门禁:

| 用户目标 | 默认入口 |
|---|---|
| 「这值得做吗/客户真的需要吗」——问题真实性待验证 | gstack office-hours(startup 六问: 需求真实性/现状替代方案/具体用户/最小楔子/观察证据/future-fit) |
| 已决定做,但客户只说了一句话 | MP grill 系(开场先确认客户是谁/现状与替代方案/痛点/成功证据四项,缺哪补哪,再展开决策树;变体见下节) |
| 只剩 2-3 个清晰方案要选 | superpowers:brainstorming |
| 需求明确,只差怎么实施 | writing-plans(单会话)或 to-spec(多会话) |
| 巨大且不知道从哪里开始 | MP wayfinder |

- office-hours 与 grill 系是**替代关系**,同一轮澄清只选其一,不连跑两套访谈。office-hours 判定「值得做」且用户拍板开工后,属于新一轮任务——带着六问结论进 grill,不重问已确认的事实。
- 副作用注意: office-hours 是双模式(startup 六问 / builder 设计脑暴),两种模式完整调用都会写 ~/.gstack 设计文档与档案(仓库外)。「只讨论」会话降级为读取并应用其六问原语,结论留在对话。
- auto 模式下本节与成熟度门禁的所有「向用户提问」环节改为自答+假设台账(SKILL.md「auto 模式」、workflows.md「auto 模式协议」);选哪条澄清链的裁决逻辑不变。
- auto 下 full 交付与高风险 focused 改动的非主链模型复核是独立门禁:需求明确、澄清链判 skip 只取消访谈,不取消复核;评审子代理必须显式选择不同模型。

## 需求成熟度门禁(full 路径的澄清阶段)

进 full 后先过「用户目标定位」(上节);确认是「已决定做」再给需求定档,选**唯一**澄清链——四档是替代关系,不得叠加成两套访谈流程:

| 需求状态 | 澄清链 |
|---|---|
| 已经明确,无待决产品决策 | 跳过澄清并说明,直接进计划(writing-plans 或 to-spec) |
| 只剩 2-3 个清晰方案要选 | superpowers:brainstorming(取批准即止,不展开访谈) |
| 一句话需求,决策树尚未展开 | MP grill 系(按下表选变体) |
| 巨大到一个上下文看不清路线 | MP wayfinder(产出决策不产出交付物;图清晰后并回 to-spec,不直跳 implement) |

### Grill 变体选择

| 条件 | 用法 |
|---|---|
| 没有代码库,压力测试一个已成形的方案/计划 | grill-me(无状态,只在对话中澄清,不落任何文档) |
| 没有代码库,问题是否真实/最小切口尚待验证 | 不进 grill——回「用户目标定位」走 office-hours |
| 有代码库,但本次不允许写文档 | 读取并应用 grilling 原语,只在对话中澄清,不写 CONTEXT.md/ADR |
| 有代码库,允许沉淀决策文档 | grill-with-docs(= grilling + domain-modeling,澄清结果写入 CONTEXT.md,满足 ADR 条件时记 ADR) |

三个变体共享同一 grilling 原语: 穷举需求决策树、一次只问一个问题、每问附推荐答案、能从环境查到的事实自己查不问用户、只把产品决策交给用户、用户确认「已形成共同理解」之前不开始执行。grill-with-docs 会写项目文档——「只讨论不改文件」的会话里不得默认调用它,降级用 grilling 原语。

### 共同理解回执(访谈的出口物)

「已形成共同理解」不靠感觉,任一 grill 变体结束访谈时固定输出回执并请用户确认;确认后才可进第二次门禁/to-spec:

```
共同理解回执
- Outcome:
- User:
- Why now / 当前痛点:
- Success evidence:
- Binding constraint:
- Out of scope:
- Unresolved decisions:
```

- 确认标准: 用户明确认可即可,短确认(是/对/ok/继续/就这样)都算,不要求长句复述。
- 停止追问的可检验条件: ①决策树各分支已走完且回执能完整填写;②能大致预测用户对接下来三个问题的回答;③Unresolved decisions 已清零或用户明确接受延期。
- 连续三轮追问没有提高理解度→停止追问,重新审视问题框架(是不是问错了问题/目标定位入错了档),而不是继续磨。
- Unresolved decisions 非空且未被接受延期时,不得进 to-spec——to-spec 只综合不访谈,欠账没人补。

### 定向调研(按需,不预载)

grilling 的「事实自己查」不限于文件系统,但默认走轻量路径,不预跑全面研究:

1. 最小项目侦察(结构/契约面/既有惯例)后即开访谈,先问信息量最大的那个问题;
2. 访谈中出现可查证的事实缺口(竞品惯例、外部约束、API 事实)→ 暂停该分支做定向调研,结果回填当前决策再继续;
3. 仅当需求天然横跨多个独立调研域(技术选型/多体系对比)才升级为 Playbook F 的并行分域调研。

调研喂访谈,不替代访谈;无目标的全面调研只会膨胀上下文、落无关文档。注意 MP research 的规则是把结论写成仓库内 Markdown——「只讨论」的会话须降级为结论进对话或会话 scratch,不落仓库。

### Grill 之后的主链(MP 官方链)

```
grill(任一变体) → 共同理解回执 → 用户明确确认(短确认即可)
  ├─ 某问题必须跑起来才能定(状态模型/UI 手感)→ handoff → prototype → handoff 回来 → 继续 grill
  └─ 过第二次门禁(规模 × 副作用授权,见下节)→ to-spec(只综合不访谈;用户确认测试 seam)→ to-tickets → 逐票执行(uncommitted ticket executor,定义见 workflows.md A.5)
```

关键约束:

- to-spec 明确「不再访谈,只综合已有对话」——grill 阶段没问透的决策,后面没有任何环节会补。共同理解回执未获确认、或 Unresolved decisions 非空且未接受延期前,不得进 to-spec。
- 上下文纪律(MP context hygiene): grill→to-spec→to-tickets 保持同一个未压缩上下文;不得已换会话用 handoff 桥接,不靠 compact 硬续。每张票的执行各自新开上下文。
- MP implement 的完成协议含 commit,superpowers subagent-driven-development 依赖 worktree/commit/按 commit 打 review 包——都超出默认授权,默认用 workflows.md A.5 的 uncommitted ticket executor;仅当用户本次明确授权 worktree+commit 时才整套调用它们。

### 第二次门禁: 共同理解确认后,先定规模再对授权

**规模出口**(MP 官方分叉,防止一句话但最终很小的需求被做成规格工程):

| 确认后的形状 | 出口 |
|---|---|
| 只要讨论结果/决策本身 | 在对话中输出结论,到此为止 |
| 单会话可完成的小需求 | 转 focused: writing-plans(必要时)→TDD 实现,不走 spec/tickets |
| 多会话/需持久规格与票 | to-spec → to-tickets → Spec 收敛门禁(workflows.md)→ 逐票执行 |

**副作用授权水位**——「不允许写文档/文件」约束的是整条链,不只 grill 本身。链上各环节的落盘/外发面: research 写仓库 Markdown、handoff 写系统临时目录、to-spec/to-tickets 按 tracker 配置写本地文件或**创建真实外部 issue**。对照水位执行,拿不准按低一档,并把受阻动作报告用户:

| 授权水位 | 允许 |
|---|---|
| 只讨论 | 一切结论留在对话;research 结论不落仓库;handoff/prototype 要写文件,先申请 |
| 允许临时文件 | handoff 只写系统临时目录(其自身规则即如此),不动工作区 |
| 允许本地工件 | spec/tickets 写仓库内约定位置(如 `.scratch/<feature>/`) |
| 允许外部发布 | 明确确认 tracker、目标项目与创建范围后,才创建真实外部 issue |

水位不自动升级;跨档需要用户本次明确授权。

## MP 流程技能的加载机制(可选集成,易踩坑)

MP 带 `disable-model-invocation: true` 的流程技能分布在 engineering 与 productivity 两个目录。下面只列本 skill 路由引用、结构档盯漂移的技能——不是全量清单,MP 升级会新增同标记技能(如 productivity 的 teach、writing-great-skills),成员以缓存目录实测为准:

- engineering: ask-matt / grill-with-docs / to-spec / to-tickets / implement / triage / wayfinder / improve-codebase-architecture / setup-matt-pocock-skills
- productivity: grill-me / handoff

这些技能不会自动触发,子代理的技能清单里可能根本看不到。**清单里没有 ≠ 不存在**。仅在插件已安装且路径可读时显式读取并应用其规则；常见缓存路径是 `~/.claude/plugins/cache/mattpocock/mattpocock-skills/*/skills/{engineering,productivity}/<name>/SKILL.md`。grilling(productivity)通常可直接用 Skill 工具调用。
- 绝不臆造同名流程冒充已调用;确实读不到就如实报告缺口,再用等效替代并说明是替代路径。
- MP implement 完成协议含 commit——默认不整套调用,逐票执行走 workflows.md A.5 的 uncommitted ticket executor;仅用户本次明确授权 worktree+commit 时才整套跑(subagent-driven-development 同理)。

## Codex 只读咨询协议(可选集成)

> 本节与 [agents.md](agents.md) 是公共版本的权威协议。Codex CLI 不可用时,跳过该镜头并如实说明,不得把缺失通道伪装成已获得第二意见。

**何时**: ①架构/取舍拿不准——先问再动手,机械明确的事不问;②高风险 delta 的对抗评审(challenge 镜头);③主链卡死需要跨模型救援;④auto 下 full 交付或高风险 focused 改动需要非主链模型独立复核,且同供应商跨档模型不可用、数据出域已获授权。

**怎么调**(任何仓库通用):

1. 把不确定点攒成一批,写成带上下文的具体问题文件: 附文件路径与约束,声明已锁定不可重议的决策。
2. 文件开头写边界声明(如「不要探索 ~/.claude 技能目录」「只读本仓库」)。
3. 解析当前已加载的 hahaliu-workflow 根目录,后台执行其 `scripts/codex-consult.sh @问题文件`(短问题可直接传文本)。`@` 前缀表示从文件读 prompt(须是当前仓库——无仓库时为当前目录——或临时目录内的普通 UTF-8 文本文件、≤512KiB),不要用 `$(cat ...)` 命令替换。脚本内部固定 `codex exec -s read-only -c 'model_reasoning_effort="xhigh"'`、prompt 经 `--` 终止符传入,并自动判断 `--skip-git-repo-check`;不得手写 codex exec 咨询调用。
4. 结论是输入不是裁决: 经 Claude 用真实代码/测试验真后才采信;真分歧摆给用户。

codex:codex-rescue 是**实现救援**通道,不是咨询通道: 其 wrapper 默认不设 reasoning effort(≠xhigh),且对非 review/diagnosis/research 请求默认加 `--write`。只在已获修改授权时使用,prompt 显式声明 read-only 或 --write;只读咨询/评审/第二意见一律走上面的 codex-consult.sh。

## 副作用边界(防御性重复)

未经用户本次明确授权,不得执行任何改变工作树、index、本地 refs 或远端状态的 Git 写命令、发布或外部副作用。**gstack ship 与 land-and-deploy 天然包含 commit/push/发布动作,不进默认路径**;用户点名要跑时,先逐项确认授权范围,能拆只读 preflight 就只跑 preflight。

## 红旗(出现即停)

- 两条主链并行(如 superpowers brainstorming 与 gstack plan 评审同时开)。
- 简单修复拉满 spec/tickets/双规划仪式;或反过来,高风险改动以「就一行」为由跳过门禁。
- 用旧测试数字、ticket 勾选状态或记忆代替当次运行证据。
- 技能清单里没有,就地即兴冒充同名流程。
- 借 ship/发版流程隐式取得 commit/push 授权。
