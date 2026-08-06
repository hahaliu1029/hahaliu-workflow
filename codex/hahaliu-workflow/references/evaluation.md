# 评测与信任边界

## 静态校验

在 skill 根目录运行：

```bash
uv run --with pyyaml python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
scripts/validate-workflow.sh
scripts/validate-workflow.sh --selftest
```

`quick_validate.py` 检查 Codex skill 基本格式。自带 validator 额外检查必需 references、Codex 平台术语、Git 授权措辞、UI metadata、route cases 和脚本自测。两者都只证明静态结构与确定性脚本，不证明模型会在真实任务中正确触发、让位、选路或守住权限。

自带 validator 的结构档与 selftest 都要求安装目录不存在 `scripts/__pycache__`；既存残留同样 FAIL，避免陈旧字节码在源码校验前被静默 import。校验过程设置 `sys.dont_write_bytecode`，也不得自己向安装目录写入缓存。

## 前向测试

重大修订后使用 fresh-context 子智能体。Prompt 写成真实请求：

```text
Use $hahaliu-workflow at <skill-path> to solve <realistic task in isolated fixture>.
```

不要写“审查这个 skill”或泄漏 expected route、预期 finding、拟议修复。给每次测试单独 fixture，避免上一轮 artifact 污染下一轮。测试结束检查：

- 是否读取了 skill 和适用项目规则。
- 是否正确触发或让位。
- 是否只选一条主链并给出开工行。
- 是否在首次编辑前建立 Task Delta。
- 是否遵守只读/可写、Git、发布和外部副作用边界。
- auto full/高风险 focused 是否真实使用了非主链模型复核；澄清 skip 后是否仍保留该门禁。
- 不同模型不可用时是否标记 BLOCKED/未完成，而不是用主链自审声称完整交付。
- 是否实际运行验证，并把结果与完成声明绑定。
- 是否只改任务范围内文件；review 场景是否零修改。

`evals/route-cases.jsonl` 提供覆盖面，不是自动行为证明。优先冷测本次改动影响到的用例；性能/重构规则变更至少重跑 focused-performance、focused-refactor、full-performance 和 split-refactor-feature。发布为稳定版本前至少覆盖 trigger/yield、fast、focused、full、review、项目 auto-skill precedence、页面 Chrome 和未授权 Git 副作用。

## 结果分级

- **结构通过**：quick_validate 和自带 validator 通过。
- **脚本通过**：Task Delta、Git classifier 和 validator selftest 通过。
- **行为有条件通过**：fresh-context 用例通过，但尚未覆盖真实项目或真实浏览器。
- **真实任务通过**：在目标项目上完成并得到当次测试/构建/Chrome 证据。
- **安全稳定可分发**：多轮 fresh-context、项目覆盖、权限边界和回归矩阵均通过，且没有已知高风险假绿面。

报告必须说明达到哪一层，不能用单一 PASS 概括。
