# 项目 auto-skill 生成配方

## 创建门槛

仅为预计持续维护至少两周的项目创建，并至少满足一项：有独特验证门禁或高风险边界；相同任务模式反复出现；全局 workflow 连续两次需要项目特判。否则继续使用全局 skill，避免 skill 泛滥。

## 放置与关系

放到 `<repo>/.agents/skills/<project>-auto-skill/SKILL.md`。项目 skill 是项目内最高业务路由，但不会自动继承全局 skill，必须重复以下不变量：

1. 用户本次指令优先。
2. 同一任务只有一条主链。
3. 未经用户本次明确授权，不执行任何 Git 写、发布或外部副作用。
4. 完成声明必须引用当次新鲜证据。

生成后运行 `git check-ignore -v` 和 `git ls-files --error-unmatch` 等只读命令，确认它是 tracked、local-only 还是由其他机制分发；在交付报告中如实说明，不能默认宣称随仓库分发。

## 必备结构

1. **启动**：支持 fast/focused/full/review，并使用统一开工行。
2. **选路表**：写清本项目四档的真实例子。
3. **升级触发**：从架构、schema、安全与核心模块中列具体路径和边界。
4. **预检**：读取项目文档、记录 `git status --short`、区分用户既有改动。
5. **主链**：说明常见任务使用哪些现有 skill 或原生 plan；不要叠加两套编排。
6. **Task Delta**：首次编辑前快照；按 ticket 私有基线；评审任务专属 patch。
7. **项目不变量**：列出 3–5 条最致命不变量并指向权威来源。
8. **验证矩阵**：按触及面列真实可运行命令和页面验收路径。
9. **Git 与交付**：固定写明授权边界和五项收尾报告。
10. **红旗**：列出本项目最常见的假绿、过度流程和错误归因。

## 生成流程

1. 读取当前项目的 `AGENTS.md`、构建/测试配置、架构/进度文档和真实入口。
2. 列出高风险边界、不变量、验证命令和现有工件惯例；没有必要时不新建进度文档。
3. 使用 `skill-creator` 初始化项目 skill，保持 `SKILL.md` 精炼，把细节放到一层 references。
4. 运行 Codex `quick_validate.py`，再运行本 skill 的 `scripts/validate-workflow.sh <项目 skill 目录>`。
5. 用 fresh-context 子智能体测试至少一个 fast、focused、full、review 和项目特有升级场景。
6. 根据真实任务迭代；静态 PASS 不能代替行为冷测。
