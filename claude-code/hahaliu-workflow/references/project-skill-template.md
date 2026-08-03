# 项目 auto-skill 生成配方

本配方用于长期维护、确实需要项目特定路由和验证门禁的仓库。

**创建门槛**(防 skill 泛滥,不满足就继续用 hahaliu-workflow 全局默认): 长期维护项目(预计 ≥2 周持续开发),且满足以下至少一条——①有独特的验证门禁/高风险边界;②任务模式反复出现;③通用路由已连续两次需要为该项目做特判。

**与 hahaliu-workflow 的关系**: 项目 auto-skill 是项目内的最高路由,覆盖全局默认。注意 **skill 之间没有自动继承**——只有被实际调用的 skill 正文会进入上下文。因此每个项目 skill 必须自带**不变量内核**(再小也不可省): ①用户本次指令优先;②唯一主链;③未经本次授权不做任何副作用(git 写/发布/外发);④完成声明必须有当次新鲜证据。其余通用裁决可写「细则见 ~/.claude/skills/hahaliu-workflow/」提示按需阅读,但不得假设它已被加载。

## 放置与命名

- 位置: `<repo>/.claude/skills/<project>-auto-skill/SKILL.md`(项目级)。生成后必须跑 `git check-ignore -v` 确认部署形态,并在交付报告写明三选一: tracked(随仓库走)/ local-only(被 .gitignore,仅本机)/ 由其他机制分发——不得默认宣称「随仓库走」。
- description 公式: 触发条件(用户调用 /<name>,或要求在本项目自主完成实现/修复/验证/复核任务) + 主链声明(按骨架 5 探测选定的主链与门禁) + 交付纪律(交付经当前证据验证的结果;有修改时声明未提交,只读时声明未修改文件)。

## 骨架(每节都要,按项目填空)

1. **启动**: 支持 `--fast / --full / --review` 旗标;开工只说一行:
   `路径: <fast|focused|full|review> | 主链: <选定主链> | 门禁: <门禁清单 或 none> | 验证: <关键命令>`
2. **选路表**: fast(文档/机械配置/明确局部改) / focused(根因或缝隙已明的单链 bug、小功能) / full(新能力/模糊需求/公共契约/跨层) / review(只读审计)。
3. **升级触发**(项目特定,最关键的一节): 列出本项目"至少 full"的高风险边界——schema/wire format/持久化格式、安全与密钥边界、核心不变量涉及的模块、同时触及 N 个以上区域。从项目 PROGRESS.md/架构文档里抄具体路径。
4. **预检**: 必读文档清单(CLAUDE.md、PROGRESS.md、CONTEXT.md、docs/adr/、docs/agents/*);记录 `git status --short` 区分用户已有改动与本任务改动;脏树是常态,不 stash 不清理;要改脏文件先留任务前副本(私有临时目录),新文件记 ABSENT。
5. **主链适配**: 先探测项目现状——已有工件惯例(issue tracker? spec 目录? docs?)、测试框架、既有主链痕迹——再选可用主链与落点;工件路径统一用探测到的 `<detected-artifact-root>`,不硬编码。若选 MP: spec/tickets 落 `<detected-artifact-root>`,tracer-bullet 垂直切票、Blocked by 声明依赖;逐票执行默认用 hahaliu-workflow workflows.md A.5 的 uncommitted ticket executor(不整套跑 MP `implement`,其完成协议含 commit)。双轴 code-review 用 `git diff --no-index` 对任务前副本算任务专属 delta,不拿整棵脏树冒充任务改动。
6. **门禁表**: brainstorming(真实架构分叉/不可逆选择时)、writing-plans(ticket 图不足以表达脆弱迁移时)、verification-before-completion(任何完成声明前,恒开)。逐票执行默认用 uncommitted ticket executor——SDD 的工作区、进度恢复与 review package 都建立在 worktree/commit 之上,不是可裁剪的叶子步骤,不得以「删掉 git 步骤」的方式借用;仅当用户本次明确授权 worktree+commit 时才完整调用 subagent-driven-development 或 MP implement。
7. **项目不变量**: 指向权威来源(如 PROGRESS.md 的不变量清单),列 3–5 条最致命的。
8. **验证矩阵**: 触及面 → 当前必须跑的命令(逐行列真实命令,如 `uv run pytest -q` / `pnpm --dir webui test`)。区分定向验证与全门禁。
9. **Git 与交付**: 固定写明「未经用户本次明确授权,不执行任何 Git 写命令、发布或外部副作用」。validator 对措辞的扫描只是 heuristic lint,不是安全证明；最终报告固定五项——用户可见结果 / 修改文件 / 实际验证命令与结果 / 未验证项与风险 / 有修改时明确说明未提交(只读任务改为声明未修改文件)。
10. **红旗**: 简单修复也强制全流程、两套体系叠加、拿整棵脏树当任务 delta、用旧测试数字代替当次证据、少跑检查把 findings 减少当修好。

## 生成流程

1. 读项目文档与真实构建/测试配置,列出高风险边界、验证命令、不变量。项目没有进度/交接文档时,把最小不变量直接写进 auto-skill 正文;**仅当用户明确要求建立交接体系时**才新建 PROGRESS.md 之类文档。
2. 按骨架填空(含不变量内核),SKILL.md 控制在 200 行内。
3. 跑当前安装的 `hahaliu-workflow/scripts/validate-workflow.sh <skill 目录>` 过结构校验(命名、四条不变量内核、选路/升级触发/验证矩阵、无隐式 commit/push、部署形态),FAIL 清零才算生成完成;部署形态写进交付报告。
4. 用 `validate-workflow.sh --evals=gate` 输出的场景提示词逐条派 fresh 子代理冷测路由(场景清单以脚本输出为准),核对选路与门禁符合预期。
5. 交付后在真实任务中迭代;升级触发清单随项目演进增补。
