# 系统架构（实际实现）

- 更新：2026-10-31
- 原则：本文件只描述**已落地并能被命令复现**的结构。计划中的能力单独列在最后一节。

## 1. 分层

```text
┌──────────────────────────────────────────────────────────────┐
│ 入口层        /web-test 命令（.opencode/commands/web-test.md）│
│               --check / --resume / 完整执行                    │
├──────────────────────────────────────────────────────────────┤
│ Agent 层      OpenCode 主 Agent + 子 Agent（general/explore）  │
│               语义分析、页面理解、测试策略、脚本编写、失败推理    │
├──────────────────────────────────────────────────────────────┤
│ 知识层        .opencode/skills/（7 个项目 Skill）              │
│               tools/knowledge_router.py（阶段→知识映射）        │
├──────────────────────────────────────────────────────────────┤
│ 编排层        tools/pipeline.py（阶段状态机 + 产物门禁）        │
│               tools/scaffold.py（用例表→测试骨架）             │
├──────────────────────────────────────────────────────────────┤
│ 执行层        tools/env_check.py（环境门禁）                   │
│               tools/run_selenium.py + tests/conftest.py        │
├──────────────────────────────────────────────────────────────┤
│ 证据层        tools/evidence.py（manifest v1.1 + SHA-256）     │
│               tools/visual_diff.py（截图差异/标注）            │
├──────────────────────────────────────────────────────────────┤
│ 交付层        tools/generate_report.py（报告）                 │
│               tools/pre_submission_gate.py（G0–G4 门禁）       │
│               tools/package_submission.py（内部交付包）        │
└──────────────────────────────────────────────────────────────┘
```

## 2. 主 Agent 与子 Agent 的分工

本次集成实际使用了 OpenCode 真实的 `task`/subagent 能力（`general`、`explore`），**没有使用 Git worktree**，因为该目录不是 Git 仓库（`git status` 返回 `fatal: not a git repository`）。替代方案：

- 先对 481 个文件做 SHA-256 基线快照（`backups/baseline-20261031-file-hashes.txt`）；
- 按文件所有权划分写入范围，子 Agent 只写独占文件；
- 共享文件（`tools/evidence.py`、`tests/conftest.py`、`tools/run_selenium.py`）由主 Agent 独占修改，子 Agent 通过契约文档依赖；
- 主 Agent 统一审核、集成、跑端到端验收。

| 角色 | 职责 | 主要产物 |
|---|---|---|
| 主 Agent | 契约冻结、共享层改造、集成、验收 | `docs/CONTRACTS.md`、`tools/evidence.py`、`tests/conftest.py`、`tools/run_selenium.py`、`tools/versioning.py`、`/web-test` |
| Agent A 环境与工具链 | 驱动版本、环境诊断、依赖锁定 | `tools/env_check.py`、`tools/driver/`、`requirements.txt`、`docs/ENVIRONMENT.md` |
| Agent B 知识与 Skill | 知识统一、Skill 安装、阶段路由 | `.opencode/skills/test-design-methodology/`、`tools/knowledge_router.py`、`knowledge/README.md` |
| Agent C 质量门禁 | G0–G4 校验器、正负样本、自测 | `tools/pre_submission_gate.py`、`tools/validators/`、`qualification/`、`tests_meta/` |
| Agent D 自主流水线 | 状态机、骨架生成、本地 fixture | `tools/pipeline.py`、`tools/scaffold.py`、`fixtures/cartcheck/`、`templates/` |
| Agent E 报告与交付 | 报告字段、内部交付包 | `tools/generate_report.py`、`tools/package_submission.py`、`submission/` |

## 3. Skills 的加载方式

### 3.1 发现

OpenCode 从 `.opencode/skills/<name>/SKILL.md` 递归发现 Skill，frontmatter 必须含 `name`（与目录同名）和 `description`。当前 7 个项目 Skill：

| Skill | 阶段 |
|---|---|
| `test-design-methodology` | 需求分析、测试设计、用例审查 |
| `test-case-design` | 用例结构化与 CS​V 落盘 |
| `browser-exploration` | 页面探索与定位 |
| `selenium-testing` | Page Object 与测试实现 |
| `visual-testing` | 截图、差异、标注 |
| `test-reporting` | 报告与缺陷清单 |
| `mooctest-web-testing` | 总调度与交付检查 |

另有 5 个外部 Skill 位于 `.agents/skills/`，本次未纳入运行时路由（仅作为参考实现）。

### 3.2 按阶段最小加载

`tools/knowledge_router.py` 是**确定性路由表**，不是提示词：

```powershell
python tools/knowledge_router.py --stage test-design --json
```

输出 `skills` / `knowledge` / `rules` / `avoid` / `notes`，并在启动时校验所有引用路径存在；缺失即非零退出。`avoid` 字段显式列出已归档的旧规则文件及其替代位置，防止 Agent 回到旧口径。

路由覆盖 11 个阶段：`requirement-analysis`、`test-design`、`case-review`、`browser-exploration`、`script-generation`、`execution`、`failure-triage`、`visual-evidence`、`reporting`、`packaging`、`quality-gate`。

### 3.3 知识权威源

| 主题 | 唯一规范来源 | 旧路径（已归档） |
|---|---|---|
| 测试方法选择、覆盖项、停止条件 | `.opencode/skills/test-design-methodology/references/method_selector.md` | `knowledge/08_derived_rules/test_design_decision_rules.md` |
| 预期判据与失败归因 | `.../references/test_oracle.md` | 同上 |
| 用例审查与覆盖率 | `.../references/coverage_review.md` | 同上 |
| 命名与证据约定 | `docs/CONVENTIONS.md` | `knowledge/08_derived_rules/submission_schema.md` |
| 规则台账与弃用映射 | `mooctest-knowledge/inventory/rule_registry.csv` | — |

BVA 口径：旧「每边 min-1/min/max/max+1 四点」已作废，改为 `MS-01` 的 2-value / 3-value 覆盖项。

## 4. 状态流转

`tools/pipeline.py` 维护 `pipeline_runs/<RUN>/state.json`：

```text
INIT → ENV_CHECK → KNOWLEDGE_LOAD → REQUIREMENT_ANALYSIS → BROWSER_EXPLORATION
→ TEST_DESIGN → CASE_REVIEW → SCRIPT_GENERATION → SCRIPT_VALIDATION
→ TEST_EXECUTION → FAILURE_TRIAGE → EVIDENCE_REVIEW → COVERAGE_REVIEW
→ REPORT_GENERATION → QUALITY_GATE → PACKAGE_PREPARATION → COMPLETE
```

- 每个阶段声明必须产物（支持 glob，`.json` 必须可解析，`.csv` 至少表头+1 行）。
- `advance` 先校验产物，缺一项就退出 1 并打印缺失清单，不允许跳阶段。
- `resume` 打印当前阶段、缺失产物、下一步动作、剩余修复预算，供新会话恢复。
- `record-repair` 每个 run 最多 3 次，超出退出 3 并提示必须 `block`。
- 流水线**不调用 LLM**：LLM 由 OpenCode Agent 承担，流水线只做确定性状态与产物门禁。

## 5. 测试数据结构

| 数据 | 位置 | 关键字段 |
|---|---|---|
| 运行/用例/证据/缺陷 | `evidence/manifest.json`（schema 1.1） | run: `status/stage/environment/notes`；case: `status/expected/actual/assertions/evidence/defects/meta`；defect: `severity/severity_rationale/category/environment/preconditions/repro_steps/repro_status/evidence` |
| 用例表 | `reports/test-cases/<slug>-test-cases.csv` | `case_id,title,priority,requirement_ids,case_type,method,preconditions,test_data,steps,expected,actual,status,automation,evidence_required,executed_in_run,notes` |
| JUnit | `reports/executions/<RUN>/junit.xml` + `junit-summary.json` | `tests/failures/errors/xfailed/cases[].status` |
| 门禁 | `qualification/gate-runs/<RUN>/gate-report.json` | `gate_status{G0..G4}`、`delivery_verdict`、`test_verdict`、`findings[]` |
| 交付包 | `submission/<RUN>/manifest.json` | 逐文件 `path/sha256/size_bytes/case_id/source`、`official_format_confirmed:false` |

### 5.1 用例级预期与实际

`tests/conftest.py` 的 `CaseContext.check()` 只写 `assertions[]`，不再覆盖用例级 `expected/actual`。用例级值只由 `case_ctx.set_expected()` / `set_actual()` 写入。这修掉了历史报告中「预期：True」的根因。

## 6. 质量门禁

`tools/pre_submission_gate.py` 分五层：

| Gate | 检查 |
|---|---|
| G0 环境与合规 | 版本字段完整、Chrome/Driver 主版本一致、AI 使用许可声明状态 |
| G1 需求与用例 | ID 唯一与格式、必填字段、可判定预期、步骤数、正向/异常/边界覆盖、需求追溯、重复检测 |
| G2 脚本与执行 | AST 语法、`pytest --collect-only` 实收集、用例↔函数映射、断言存在、无 `time.sleep`、JUnit 与 manifest 交叉核对 |
| G3 缺陷与证据 | manifest 哈希/缺失/跨 run/重复、passed 用例必须有证据、failed 用例必须有归因或缺陷、缺陷字段完整性 |
| G4 交付包 | 目录结构、xlsx 可打开、zip 可解压、文件哈希与 manifest 一致 |
| G5 官方 2025 布局 | 10 列用例表、`<App>_R<req>_<seq>` 编号、`<11位时间戳>_<编号>.png` 截图、`screenshots/` zip、一需求一函数的代码骨架、`take_screenshot` 未被修改 |

**双结论**：

- `test_verdict`：被测应用是否通过测试。
- `delivery_verdict`：测试成果是否可信、可交付。

真实产品缺陷导致 `test_verdict=FAIL`，只要缺陷已确认并取证，`delivery_verdict` 仍可为 `PASS`。这样门禁拦的是「不可信的成果」，而不是「被测系统有 Bug」。

### 6.1 2025 官方布局适配

比赛交付使用**独立适配层**，不污染内部约定：

```text
内部 run（manifest + 16 列 CSV）
        │  tools/export_official_2025.py
        ▼
official_2025/<RUN>/  10 列 xlsx + screenshots/ + screenshots.zip
                      + Test<App>.py（一需求一函数）+ runner/（可运行实现）
```

`--verify` 与门禁 **G5** 校验官方结构；详见 `docs/OFFICIAL_2025.md`。
2026 培训视频的规则已整理（见 `docs/COMPETITION_RULES_2026.md`）；2026 赛题包未获取，导出件仍只标 `2025-baseline-only`，待赛题包复核。

## 7. 证据归档

```text
evidence/
  raw/<RUN>/<CASE>/          原始截图、页面源码（不可覆盖）
  annotated/<RUN>/<CASE>/    标注图、裁剪图
  diff/<RUN>/<CASE>/         差异图、热力图、metrics.json
  logs/<RUN>/                运行日志、用例日志、浏览器控制台
  manifest.json              唯一索引（SHA-256 + size_bytes）
```

登记时强制：
- 路径必须在 `evidence/<bucket>/` 下；
- 路径中的 `RUN-*` 必须与登记 run 一致（跨 run 拒绝）；
- 同 run 同路径不得重复登记；
- `passed` 用例必须有断言或证据。

## 8. 已知限制（实现层面）

1. **不是 Git 仓库**，无法用 worktree/分支隔离并发；改用基线哈希 + 文件所有权。
2. **子 Agent 会话里 MCP 浏览器未连接**，浏览器探索需用 Selenium 或 `playwright-cli` 兜底。
3. **MCP 交互存在差异**：`fill` 追加文本、`press Enter` 可能不提交、截图需先 focus 且落在 server-local 临时目录。
4. **`test-design-methodology` 的草案目录保留为只读副本**，与安装副本之间目前只有文档约束，没有自动 diff 门禁。
5. **2026 官方提交格式未确认**，交付包只能标为内部演练包（`official_format_confirmed:false`）。
6. **AI 使用许可未确认**，正式比赛使用需另行授权。
