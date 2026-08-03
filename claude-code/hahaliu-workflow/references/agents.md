# Agent 分工

本文件是公共版本的分工权威：机械/批量任务优先较低成本模型；评审/架构/安全使用最强可用模型；独立任务可并行,有依赖的任务串行。用户或项目规则更严格时,叠加执行更严格约束。

## Roster: 场景 → 子代理 → 模型档

| 场景 | 派谁 | 模型档 | 说明 |
|---|---|---|---|
| 只读侦察、多文件扫描、定位代码 | Explore | sonnet | 只要结论不要文件转储;声明广度(medium / very thorough) |
| 实现一个独立 ticket/切片 | general-purpose | 继承主模型 | 历史主力(96% 的派发);prompt 按下面检查单写 |
| 深度规划/架构方案 | 主上下文自己做,或 ecc:planner | 最强档 | 规划是高杠杆决策,不下放低档 |
| 代码评审镜头 | ecc:code-reviewer 或对应语言 reviewer(python/react/typescript…) | 最强档 | 它们要求 >80% 置信度才报、零发现是有效结论 |
| 安全审查 | ecc:security-reviewer | 最强档 | 触及认证/密钥/注入面/用户输入时 |
| 构建/类型报错修复 | ecc:build-error-resolver(或语言版) | sonnet | 只修构建,最小 diff,不做架构性改动 |
| 架构咨询/对抗评审/第二意见 | `scripts/codex-consult.sh "<prompt>"`(长问题用 `@文件`;协议见 routing.md) | wrapper 内部固定 xhigh | Codex CLI 可用时的可选通道；调用方不加任何 flag、不手写 `codex exec`;只读,结论经验证后才采信 |
| 实现救援(仅已获修改授权时) | codex:codex-rescue | wrapper 为 sonnet,effort 默认不设(≠xhigh) | 它对非 review/diagnosis/research 请求**默认加 --write**;prompt 必须显式写 read-only 或 --write,不靠它猜 |
| 测试纪律辅导 | ecc:tdd-guide | sonnet | 需要外部视角检查测试质量时才派 |

## 并行规则

1. 只读任务(调研、侦察、冷读评审)可放开并行,一个问题域一个 agent,同一条消息里批量派发。
2. 实现子代理不并行编辑共享契约、共享状态或同一文件;要并行必须先按**文件所有权**切分,边界写进各自 prompt。
3. 有依赖的串行推进,一次只推进一个垂直切片(frontier ticket)。
4. 多评审视角(Standards 轴 / Spec 轴 / 安全轴)必须上下文隔离、并行独立产出,不互相稀释。
5. 协调与最终综合始终留在主上下文,不外包;子代理要偏离其目标契约时,先回报主上下文更新契约,不得自行扩权。

## 子代理 prompt 检查单(每次派发过一遍)

- [ ] 自包含: 每个子代理有**专属目标契约**(目标/范围/验收标准)与**明确交付物**,附涉及文件路径、验证命令,不依赖主会话上下文。
- [ ] 边界: 文件所有权、非目标、不许顺手重构。
- [ ] **禁止 Git 写操作**：未经用户本次明确授权,不执行任何改变工作树/index/本地 refs/远端状态的 Git 命令,也不发布——逐字写进 prompt。
- [ ] 返回约定: 完成给证据;不行就返回 BLOCKED / NEEDS_CONTEXT,不许假装完成。
- [ ] 模型: 默认继承,只在明确匹配上表档位时显式指定。

子代理返回 BLOCKED/NEEDS_CONTEXT 时,由主上下文补足上下文或停下来处理,不重派同样的 prompt 硬闯。
