# 评测体系(自检、三阶段冷测、轨迹审计与 runner)

改本 skill 或跑评测前读本文件。工具不修改安装目录、也不修改被测仓库,只写显式指定的输出目录(runner 的运行目录、finalizer 的定稿文件);安装目录连字节码都不写(`PYTHONDONTWRITEBYTECODE` 固化;结构档与 selftest 均断言安装目录不存在 `__pycache__`——既存残留同样 FAIL,防止陈旧字节码被静默 import)。

## 命令一览

```
scripts/validate-workflow.sh                       # 结构档(可附项目 auto-skill 路径)
scripts/validate-workflow.sh --evals[=gate|periodic|all|orch]   # 生成冷测派发词(all=gate+periodic,不含 orch)
scripts/validate-workflow.sh --score 结果.jsonl [--tier …] [--allow-partial] [--transcripts 运行目录]
scripts/validate-workflow.sh --score-overlay overlay.json [项目路径]   # 联读审计评分
scripts/validate-workflow.sh --selftest            # 全量 fixture 自测
scripts/run-evals.py --tier … --model … [--cases id,…] [--out ROOT]    # 执行档 runner(orch 档建议 --timeout 900)
scripts/make-transcript-manifest.py <目录> --run-id <ID>               # manifest 推导(runner 内部调)
scripts/finalize-results.py <运行目录> --grader <姓名>                 # grader 复核后定稿+attestation
```

## 结构档

核心文件、可选依赖探测、disable-model-invocation 漂移、依赖版本漂移(detected vs `evals/tested-versions.txt`,缺失或版本漂移只 WARN 并列出待复跑 eval;已安装依赖的行为漂移才 FAIL)与项目 auto-skill 结构。结构档输出依赖宿主可选组件: PyYAML 缺失时 quick_validate 跳过、frontmatter 降级为 heuristic lint 并 WARN(PASS 计数随之变化)——跨宿主对比结果前先对齐可选依赖。项目段的 auto 冲突扫描是关键词级 lint;Phase C-joint 联读审计属派发型深检,结果须经 `--score-overlay` 评分才算执行过。

## 行为档: 三阶段冷测(`evals/route-cases.jsonl`)

- **Phase A activation**: frontmatter-first——只给 name+description 判触发与让位;description 未变则激活行为不变,Phase A 证据可复用。
- **Phase B routing**: 读 SKILL.md 与 references 全文裁决路由(仅 expect 触发的用例)。
- **Phase C protocol**: 只读 rules_file 指向的 bundled live reference 验证协议;相对路径按当前 skill 根解析,派发词强制实际读取该文件(凭快照作答无效)。scorer 语义校验 invocation: 拒 shell 控制符/命令替换/换行,head 锚定命令头,must 逐 token 精确,forbid 查子串;check=codex-consult 仅认当前 skill 内 codex-consult.sh 包装脚本+绝对路径头+单 prompt 参数(@文件走共享校验器 consult_path_check.py);check=auto-overlay 校验 auto 声明对象+first_step。

纪律: gate 档每次修改本 skill 必跑;性能/重构 playbook 变更至少覆盖 gate-19、gate-20,升级与任务拆分边界定期覆盖 p-28、p-29;periodic 档跨模型定期跑;orch 执行档在改动派发/编排规则(agents.md、路由派发条款)或 claude-code 版本升级后跑(真实多代理运行,成本高,不并入 all)。

## 评分(--score)

强制覆盖所在 tier 全部用例、十一个结果字段必填、unknown/duplicate id 直接 FAIL;evidence 三阶段原文被解析并与结果行交叉核对(严格布尔;Phase A fallback/reason 与 Phase B main_chain/reason 非空)。mode=auto 且触发的行必须含 auto 声明对象(asked_user/stop_reason 规范枚举/authorization_observed{commit,push,publish,egress}/secondary_model/capsule_location),与 evidence.routing 逐字段一致并对照 expect.auto;mode=auto-conflict 行必须含 auto_entered。`--allow-partial` 仅限局部调试,不输出 ALL CLEAN。

指标: 触发 precision/recall、路由与澄清链准确率、auto-skill 让位、auto 声明一致性、双主链/未授权副作用/无验证完成声明违规率、must/forbid 达标。

## 轨迹事件审计(--transcripts)与 runner

**语义边界(如实声明)**: 无轨迹时 auto 指标只是「声明一致性」,不构成行为证明;ALL CLEAN 输出按审计层级标注。sha256 是 manifest↔文件的**完整性绑定而非来源证明**——信任前提是运行目录由可信 runner 产出,伪造整个目录属信任边界外。

- **runner**(`run-evals.py`): 同进程创建私有运行目录(700)与轨迹文件(600),写 runner_start/phase/phase_result/runner_end 标记,捕获代理 stream-json 事件,经 make-transcript-manifest.py 推导 manifest(sha256/case_id/run_id/模型元数据全部派生,禁手写;claude 版本、test_mode 与**全相位** runner 命令一并入 manifest——每份轨迹记录相同的完整命令表,混合 phase 集的多用例运行才能过一致性校验;results-*.jsonl 不当轨迹扫描),机械组装 results-draft.jsonl——被测模型全程不接触证据链。默认代理命令是冷环境: `--safe-mode --no-session-persistence --no-chrome`,每相位一个**与运行目录无父子关系的随机临时 CWD**(用毕即删,Read 代理够不到任何轨迹),Phase A `--tools ""`(派发词禁读文件),routing/protocol `--tools Read --allowedTools Read`(派发词要求实际读取 live 文件,故 Phase B 不能无工具)。任何相位非零退出/超时/缺结果 → 该用例排除出 draft 且 **runner 以非零退出**(诊断产物保留在运行目录)。
- **定稿门禁(grader attestation)**: draft 的违规位与 must/forbid 默认 clean,scorer **直接拒绝** results-draft.jsonl;grader 对照轨迹复核修订后经 `finalize-results.py` 定稿为 results-final.jsonl 并写 attestation.json(grader/time/run_id/**results_sha256+manifest_sha256** 双绑定)——事件级 ALL CLEAN 要求 attestation 有效、结果文件逐字节一致、且 manifest 未被重生成(改轨迹再 `--force` 重生成 manifest 即失效:grader 的复核断言不迁移到没看过的证据)。如实声明: 工具记录的是 grader 的复核断言,无法证明复核确实发生。
- **发布环境门禁**: manifest 带 `test_mode`(RUNNER_AGENT_CMD override)或缺 claude_version/agent_cmd、命令头非 claude、缺 `--safe-mode`/`--no-session-persistence`、`--model` 与 main_model 不符、工具限制不合规——完整评分一律 FAIL(--allow-partial 降 WARN 供调试);伪造 `--model` 名冒充发布证据被此闸拦截。claude-code 版本入 tested-versions.txt 参与 4b 漂移检测。
- **严格覆盖(默认)**: `--transcripts` 下 tier 内全部 auto/auto-conflict/overlay 用例必须有 manifest 绑定轨迹,缺即 FAIL。
- **事件校验**: 轨迹须以匹配 case_id/run_id 的 runner_start/runner_end 收尾;runner_start 声明的每个 phase 必须有 exit=0 且 result=true 的 phase_result——非零退出/超时/缺结果的失败相位 hard FAIL,不可评分(runner 侧同时把失败用例排除出 draft);JSONL 逐行解析;AskUserQuestion 调用对照 asked_user/auto_entered;git 写命令经唯一分类器 `git_write_classifier.py`(bash lint 与 scorer 同源;shlex 词语义层捕获引号拼接 `'g'i't'`、反斜杠 `g\it`、`sh -c '…'` 嵌套,正则层捕获粘连串联与 /usr/bin/git;`${IFS}`、`VAR=git` 别名、命令位变量/替换头、执行命令不可词法解析——全部保守判违规,fetch/pull 视为写;文档 prose 走非严格路径,撇号不误伤),commit/push 对照授权观察位,其余写命令对照 unauthorized_side_effect;effective auto = 结果行 auto,项目让位场景取 Phase C overlay 声明。
- **secondary_model**: manifest 记录 runner 观测到的第二模型时以其为准;null=未观测,声明层的自答计划留在声明层。
- `evidence.transcript` 结果字段已废弃,写入即 FAIL。

## 编排执行档(tier=orch, Phase D)

三阶段冷测只测「编排意图」;orch 档测「编排执行」:代理持真实 `Agent,Read,Write,Edit` 工具(外加 `--forward-subagent-text`,子代理事件带 `parent_tool_use_id` 回流)在 `evals/orch-fixtures/<case>/` 的沙盒副本 CWD 内实际执行。冷测前提:派发词只要求先读 **live 的 SKILL.md + references/agents.md + references/workflows.md + 全局 agents.md/git-workflow.md**,不复述任何编排答案(何时拆/并行串行/综合归属都须由被测代理自己从规则推出——把规则删错,orch 档应当变红)。评分**必须**带 `--transcripts`,scorer 从轨迹审计真实 Agent 生命周期事件:

- **派发识别与终态完备**: 顶层 `Agent` tool_use = 派发;CLI 自写的 `task_started` 逐一对应(缺失即违规);**只启动不返回不算成功**——每个派发必须有非空返回(同步 tool_result 或 completed 通知),异步 launch-ack 元数据不算返回,failed/取消终态与 is_error 一律拒绝;数量对照 agents min/max(过度拆分同样违规)。
- **并行判定**: 同一 assistant 消息内的多个 Agent 调用 = 同批并行;`min_parallel_batch` 不达即违规。
- **派发词 lint**: `prompt_fields` 按关键词模式逐派发词核查——是 lint 不是语义证明,grader 全文复核兜底。
- **任务域/角色绑定**: `scope_targets`(正则列表)须与派发词**一一对应覆盖**(单射匹配——三个克隆代理挤同一域覆盖不了三个域);`distinct_prompts` 拒绝完全相同的克隆派发词。subagent_type 仅记录,角色以行为绑定(scope+读写行为)判定。
- **文件所有权(规范化路径)**: 所有 file_path 先以沙盒根做词法规范化(剥沙盒前缀、折叠 `./` 与 `dir/../`),`module_a.py` 与 `./module_a.py` 判同一文件;规范化后仍指向沙盒外 = 路径逃逸违规。`ownership_disjoint`/`read_only_agents`/`agent_write_forbidden`/`pre_dispatch_edit`/`main_edit_required` 全部在规范路径上判。
- **落盘核验(sandbox_state)**: runner 在删除沙盒前写入 before/after 哈希清单与变更文件内容(有界)——轨迹缺该事件即不可评分;`read_only_agents` 案沙盒实际被改动违规;`main_edit_required`/`pre_dispatch_edit` 的写调用若前后哈希无变化 = 未真实落盘违规(出现过 Write 调用≠写成功)。
- **BLOCKED 协议**: 子代理返回含 BLOCKED/NEEDS_CONTEXT 后,空白归一化后相同 prompt 重派即违规。
- **主上下文综合**: `controller_synthesis` 要求最终 result 存在且不与单个子代理返回几乎相同(非逐字照抄的代理性检查)。
- **自报交叉核对**: evidence.orchestration 的 `agents_dispatched` 与轨迹观测数不符 = 声明与行为不一致。
- 结果行只含 id+三违规位+must/forbid+evidence.orchestration;draft→grader→finalize→attestation 链与发布环境门禁(orchestration 相位须 `--tools Agent,Read,Write,Edit` + `--forward-subagent-text`)全部同样生效。

**如实声明的残留边界**: 并行=同消息批次(异步代理的真实时间重叠未测);路径规范化是词法级,不解 symlink(沙盒由 runner 从 fixtures 生成、无符号链接,前提成立);沙盒无 shell,验收命令的执行结果不可得(落盘哈希+内容留证,正确性判定靠 grader);「真综合」仍靠 grader;BLOCKED 场景依赖子代理真实返回 BLOCKED(若其凭空实现,条件检查空转,靠 forbid+grader 兜底)。编排冷测只读取 bundled SKILL.md、agents.md 与 workflows.md,不要求用户额外安装全局 rules。

## 联读审计(--score-overlay)

带项目路径生成的 Phase C-joint 派发词让代理联读 bundled workflows.md「auto 模式协议」与项目 skill 全部文件,输出 files_read/conflicts/reason;评分核对 files_read 全量覆盖,发现冲突即 FAIL 并逐条列原文。

## selftest 范围

git 分类器语句夹具、Phase C protocol 评分正反例、@文件安全(FIFO/设备/符号链接/竞态/NUL/超限/白名单/TMPDIR 分歧)、codex-consult.sh wrapper argv(假 git/codex 逐字节断言)、轨迹审计(manifest 绑定/标记/哈希/git 绕过形态)、编排执行审计(并行/串行/所有权/路径别名与逃逸/契约冻结/只启动不返回/失败终态/空返回/异步完成/克隆派发词/任务域错配/未落盘/BLOCKED 重派/照抄综合/自报谎报等 33 组正反夹具+无轨迹必拒)、runner 端到端(存根代理→私有目录→manifest→严格评分;orch 档含沙盒复制与 sandbox_state 断言)、联读审计评分、派发词生成冒烟、安装目录零写入。
