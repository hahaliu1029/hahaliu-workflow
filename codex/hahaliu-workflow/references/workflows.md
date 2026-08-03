# 端到端工作流

## 新功能

1. 读取项目规则、项目 auto-skill、真实入口、契约面和现有测试缝隙。
2. 按 routing.md 选择唯一澄清链。能从代码、文档或当前环境查到的事实自己查；只把会改变产品结果的决策交给用户。
3. 建立目标契约和原生 plan。跨层改动先串行冻结共享 schema、API 形状和兼容策略。
4. 按最小垂直切片推进。每个切片在首次编辑前建立自己的 Task Delta 基线；先写能失败的验收/回归证据，再实现最小代码。
5. 对切片 patch 做 Standards 与 Spec 双轴评审；涉及安全边界时追加安全轴。
6. 逐条重放验收标准，发现遗漏就补切片并重新验证，直到计划、实现和证据一致。

## Bugfix

1. 构造最窄复现并保存失败证据。
2. 根因未知时完整使用 `superpowers:systematic-debugging`，定位因果链后再改代码。
3. 建立回归测试或等价的可重复失败检查，确认修复前会失败。
4. 用 `superpowers:test-driven-development` 或项目等价流程完成最小修复。
5. 复跑最窄检查，再跑受影响区域的回归；只评审本任务 delta。

## Review 与诊断

1. 保持只读；先锁定用户给定的 diff、文件、分支或运行态范围。
2. 读取真实调用链和当前证据。需要运行命令时优先可重复、非变异检查。
3. 按 correctness/standards、spec compliance、安全和运行风险分轴。
4. finding 包含严重度、精确位置、触发条件、影响和证据。没有可行动 finding 时明确说没有，并列出未覆盖范围。
5. 不修改文件，最终明确声明本次未修改文件。

## 页面 QA

1. 先识别本地、测试、预发或生产环境；未知环境按生产处理。
2. 遵守当前 `AGENTS.md` 和用户指定的浏览器约束；用户要求真实 Chrome 或真实登录态时，直接控制对应浏览器，不改用内部浏览器、模拟器或其他自动化工具。
3. 覆盖关键导航、表单、空态、错误态、权限态、响应式行为和 console/network 异常。
4. 可能写真实业务数据或触达外部的操作，在执行前逐项取得授权。
5. review 路径只报告；focused/full 路径在授权范围内修复后用同一真实路径复验。

## 发版准备度

默认只做 read-only preflight：检查任务 delta、版本/迁移兼容、测试矩阵、构建产物、回滚路径和未决风险。`ship`、`land-and-deploy` 或类似流程只在用户明确授权其具体 commit、push、PR、merge、deploy 范围后使用；不能从“发版检查”推断这些权限。

## Goal 与持续执行

用户显式使用 `/goal`、要求“完成为止”或产品提供 active goal 时：

1. 把目标契约作为唯一完成定义，维护可验证 plan，并持续推进安全、在范围内的下一步。
2. 持续执行不扩大文件、Git、发布、出域或真实业务副作用授权。
3. 在稳定边界记录当前阶段、已完成项、验证证据、假设、风险和下一步；上下文压缩后先与 live 文件及状态对账。
4. 只有目标确实完成且没有必需工作剩余时标记 complete。平台对 blocked 的判定和连续轮次阈值以当前 system 指令为准。

## Task Delta Adapter

修改类任务不能用 `git diff ... HEAD` 判断本次归属，因为工作树可能在任务开始前已脏。优先使用本 skill 的 `scripts/task-delta.sh`：

```bash
SNAP_DIR=$(scripts/task-delta.sh begin)
scripts/task-delta.sh capture "$SNAP_DIR" path/to/file another/file
# 现在才编辑已 capture 的文件
scripts/task-delta.sh render "$SNAP_DIR" --save
scripts/task-delta.sh cleanup "$SNAP_DIR"
```

规则：

1. 每个任务或 ticket 以自己开始时刻为基线；首次编辑文件前 capture。
2. 只有文件此刻确实不存在才记 ABSENT。前一任务创建的未跟踪文件若已存在，必须作为 FILE 基线。
3. `.env`、密钥、证书、数据库、大型二进制和私有数据不进入快照、patch 或子智能体 prompt；只记录路径与必要哈希并本地评审。
4. render 使用 `git diff --no-index` 聚合当前任务 patch；退出码 1 代表存在差异，不是失败。
5. 收尾用 `git status --short` 交叉核对触及面。出现未 capture 的改动时，披露归因缺口，不臆造专属 diff。
6. patch 用于评审与报告，不能自动 stage、commit 或覆盖工作区。

## 验证分级

| 风险 | 当次证据 |
|---|---|
| 文档/文案 | 定向查找、格式/链接校验、必要的渲染检查 |
| 局部逻辑 | 最窄回归测试 + 受影响模块测试 |
| 类型/API | 定向测试 + typecheck/contract 检查 |
| 跨层/full | 定向测试 + 全量相关门禁 + 验收标准重放 |
| 页面行为 | 构建/测试 + 真实 Chrome DOM、交互、console/network 证据 |
| 发版/高风险 | 完整矩阵、迁移/回滚检查和未验证风险列表 |

测试或 validator 的含义要如实分层：结构检查证明结构，单元测试证明覆盖到的逻辑，构建证明可构建，浏览器 smoke 证明观察到的路径；任何一层都不能冒充完整可用性。

## 收尾报告

```text
结果: <用户可见结果> | 路径: <fast|focused|full|review>
修改: <任务专属文件或“未修改文件”>
验证: <当次命令/浏览器路径 + 关键结果>
风险: <未验证项、原有失败、环境阻塞>
状态: <未提交；或逐项列出用户已授权的 Git/发布动作>
```
