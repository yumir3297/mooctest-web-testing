# 测试流水线（Autonomous Testing Pipeline）

本文件描述 `tools/pipeline.py`、`tools/scaffold.py` 与 `fixtures/cartcheck/` 构成的确定性执行骨架。
它服务于 2026 全国大学生软件测试大赛 Web 应用测试赛道，也可以用于任何本地 Web 应用的冷启动演练。

> **边界声明：本流水线不自动调用 LLM。** LLM 由 OpenCode Agent 承担；流水线只做确定性状态管理、产物登记与门禁校验。
> 流水线不会生成需求、用例或报告内容，也不会替 Agent 做判断。

## 1. 目标与非目标

目标：

- 把「需求分析 → 用例设计 → 用例审查 → 浏览器探索 → 脚本生成 → 执行 → 失败归因 → 证据复核 → 覆盖复核 → 报告 → 质量门禁 → 打包」固定为 17 个有序阶段。
- 每个阶段有明确的**必须产物**。没有产物就不能推进，避免「口头完成」。
- 新会话可以通过 `resume` 在一条命令内恢复上下文。
- 受控修复有硬预算（每个 run 最多 3 次），防止无限重试掩盖真实问题。

非目标：

- 不自动编写测试逻辑、不自动分析需求、不自动判定缺陷。
- 不修改被测系统业务代码。
- 不替代 `evidence.py`、`run_selenium.py`、`generate_report.py`、`pre_submission_gate.py`、`package_submission.py`；流水线只调用其产物文件（或在存在 CLI 时打印建议命令）。
- 不做远程提交、不扫描未授权目标。

## 2. 阶段、执行者与必须产物

`tools/pipeline.py` 中 `STAGES` 是唯一的阶段表；下表与代码保持同步。

| # | 阶段 | 由谁执行 | 必须产物（相对项目根，支持 glob） |
|---|---|---|---|
| 1 | `INIT` | 程序：`pipeline.py init` | `pipeline_runs/<run>/state.json`、`pipeline_runs/<run>/requirement.md` |
| 2 | `ENV_CHECK` | 程序：`tools/env_check.py`；Agent 解读 | `pipeline_runs/<run>/env_check.json` |
| 3 | `KNOWLEDGE_LOAD` | 程序：`tools/knowledge_router.py`；Agent 选择知识 | `pipeline_runs/<run>/knowledge_plan.json` |
| 4 | `REQUIREMENT_ANALYSIS` | Agent | `pipeline_runs/<run>/requirements.json`、`reports/test-cases/*<slug>*requirements*.md` |
| 5 | `BROWSER_EXPLORATION` | Agent（浏览器 MCP / Selenium 探索） | `reports/executions/<run>/exploration.md`、`evidence/raw/<run>/**`（至少 1 个文件） |
| 6 | `TEST_DESIGN` | Agent | `reports/test-cases/*<slug>*test-cases.csv`、`reports/test-cases/*<slug>*test-cases.md` |
| 7 | `CASE_REVIEW` | Agent | `pipeline_runs/<run>/case-review.md` |
| 8 | `SCRIPT_GENERATION` | 程序：`tools/scaffold.py` 生成骨架；Agent 补全 | `tests/generated/<slug>/test_*.py`、`tests/generated/<slug>/page_*.py` |
| 9 | `SCRIPT_VALIDATION` | 程序：`pytest --collect-only` + 静态门禁 | `pipeline_runs/<run>/script-validation.json` |
| 10 | `TEST_EXECUTION` | 程序：`tools/run_selenium.py` | `reports/executions/<run>/junit-summary.json` |
| 11 | `FAILURE_TRIAGE` | Agent（结合 JUnit、日志、截图） | `pipeline_runs/<run>/triage.md`（无失败也要写「无失败」说明） |
| 12 | `EVIDENCE_REVIEW` | 程序：`evidence.py verify`；Agent 复核 | `pipeline_runs/<run>/evidence-review.json` |
| 13 | `COVERAGE_REVIEW` | Agent | `pipeline_runs/<run>/coverage.md` |
| 14 | `REPORT_GENERATION` | 程序：`tools/generate_report.py`；Agent 校对 | `reports/executions/<run>/report.md`、`reports/executions/<run>/report.json` |
| 15 | `QUALITY_GATE` | 程序：`tools/pre_submission_gate.py` | `qualification/gate-runs/<run>/gate-report.json` |
| 16 | `PACKAGE_PREPARATION` | 程序：`tools/package_submission.py` | `submission/<run>/submission.zip`、`submission/<run>/manifest.json` |
| 17 | `COMPLETE` | Agent 写交付说明；程序 `verify-run` | `pipeline_runs/<run>/FINAL.md` |

### 2.1 产物校验规则

`advance` 只做确定性文件校验，不 import 任何兄弟模块：

- 路径必须存在且是文件；空文件失败。
- `.json` 必须能被 `json.load` 解析（兼容 UTF-8 BOM / UTF-16 重定向输出）。
- `.csv` 至少有 2 行非空内容（表头 + 至少 1 条数据）。
- glob 必须至少匹配到一个通过内容校验的文件；同一模式匹配多个文件时，至少一个有效。
- 目录不会被当作产物；`evidence/raw/<run>/**` 只统计其中的文件。

对 `ENV_CHECK`、`KNOWLEDGE_LOAD`、`QUALITY_GATE` 等依赖其它模块的阶段，`advance` 只校验文件。
若对应 CLI 存在，命令会打印建议（例如 `python tools/pre_submission_gate.py ...`），但**不会自动执行**。

## 3. 状态契约

状态文件：`pipeline_runs/<RUN-ID>/state.json`，schema v1.0。

```jsonc
{
  "schema_version": "1.0",
  "run_id": "RUN-X",
  "target": "http://127.0.0.1:8765/",
  "requirement": "fixtures/cartcheck/REQUIREMENTS.md",
  "scope": "smoke",
  "slug": "cartcheck",
  "status": "running",              // running | failed | blocked | complete
  "current_stage": "TEST_DESIGN",
  "stages": [
    {"name": "INIT", "status": "done", "started_at": "…", "finished_at": "…",
     "note": "", "artifacts": ["pipeline_runs/RUN-X/state.json"]}
  ],
  "artifacts": {},                  // set-artifact 的人工登记，不参与 advance 门禁
  "repairs": [],                    // 最多 3 条
  "repair_limit": 3,
  "revision": 3,
  "created_at": "…", "updated_at": "…", "finished_at": null
}
```

阶段状态：`pending → running → done`，异常时 `failed`；运行状态：`running → failed | blocked | complete`。

## 4. CLI

```powershell
# 初始化（已存在则退出 2，必须显式 --force）
python tools/pipeline.py init --run-id RUN-20261101-01 `
  --target http://127.0.0.1:8765/ `
  --requirement fixtures/cartcheck/REQUIREMENTS.md `
  --slug cartcheck --scope smoke

# 查看状态（--json 供程序读取）
python tools/pipeline.py status --run-id RUN-20261101-01 --json

# 校验当前阶段产物并推进
python tools/pipeline.py advance --run-id RUN-20261101-01

# 标记当前阶段失败 / 整体阻塞
python tools/pipeline.py fail  --run-id RUN-20261101-01 --reason "…"
python tools/pipeline.py block --run-id RUN-20261101-01 --reason "…"

# 新会话恢复
python tools/pipeline.py resume --run-id RUN-20261101-01

# 记录受控修复（硬上限 3 次，第 4 次退出 3）
python tools/pipeline.py record-repair --run-id RUN-20261101-01 `
  --class LOCATOR --action "…" --result "…"

# 登记产物 / 整体自检
python tools/pipeline.py set-artifact --run-id RUN-20261101-01 --key report --path reports/executions/RUN-20261101-01/report.md
python tools/pipeline.py verify-run --run-id RUN-20261101-01
```

退出码：

| 码 | 含义 |
|---|---|
| 0 | 成功，或幂等无操作（阶段已完成、resume 等） |
| 1 | 产物门禁失败；`verify-run` 自检失败；对 blocked run 调用 advance |
| 2 | 用法/状态前置条件错误：非法 run id、run 不存在、重复 init 未加 `--force` |
| 3 | `record-repair` 预算耗尽，必须转 `block` |

`init` 会：

1. 校验 run id 形如 `RUN-...` 且不允许路径穿越；
2. 把需求文件复制为 `pipeline_runs/<run>/requirement.md`（原文件保持不变）；
3. 创建 17 个阶段条目，`INIT` 为 `running`，其余为 `pending`；
4. 写入 `state.json`（原子替换）。

`advance` 会：

1. 若当前阶段已 `done`，打印提示并退出 0（幂等）；
2. 校验当前阶段的全部必须产物；
3. 任一缺失/无效则打印清单并退出 1，不修改状态；
4. 全部满足则写 `finished_at`、将阶段置 `done`、登记实际产物路径、`revision+1`；
5. 启动下一阶段并打印下一步动作与建议命令；`COMPLETE` 完成后 run 状态变为 `complete`。

`block` 会写 `state.json`，并调用 `python tools/evidence.py update-run --run-id … --status blocked` 同步 manifest；
manifest 同步失败只记录在 `state.manifest_sync`，不阻断 block 本身。

## 5. 修复预算

- 每个 run 最多 3 次 `record-repair`，这是硬预算，不是提示词。
- 第 4 次调用退出 3，并提示必须 `block`。
- 每条修复记录：时间、当前阶段、分类、动作、结果。
- 分类枚举：`ENV`、`LOCATOR`、`TIMING`、`DATA`、`SCRIPT`、`ASSERT`、`APP`、`UNKNOWN`。
- 预算用尽不等于失败结论；如果仍无法继续，应 `block` 并交给主 Agent/人工判断。

## 6. 恢复流程（新会话）

```powershell
python tools/pipeline.py status --run-id RUN-X
python tools/pipeline.py resume --run-id RUN-X
```

`resume` 输出：

1. run 状态、目标、scope；
2. 当前阶段及其状态；
3. 下一步必须做什么（阶段表里的 `next_action`）；
4. 当前阶段缺失产物清单；
5. 修复预算余额与已有修复记录；
6. 阻塞原因（若有）。

恢复时的推荐顺序：

1. 先看 `resume` 的缺失产物，不要重复已完成阶段；
2. 只补当前阶段的产物，然后 `advance`；
3. 修复一次就 `record-repair` 一次，保留真实原因与结果；
4. 预算耗尽或环境不可用时 `block`，不要伪造产物；
5. 全部阶段完成后运行 `verify-run`，再进入交付。

## 7. 与 `/web-test` 的关系

`/web-test` 是面向 Agent 的编排入口（需求分析、用例设计、探索、Selenium、视觉取证、报告）。
本流水线是它下面的**确定性状态与门禁层**：

- `/web-test` / 各 Skill 决定「怎么做、做什么判断」；
- `pipeline.py` 决定「当前在哪个阶段、产物是否齐全、能否推进」；
- `scaffold.py` 把 CSV 用例机械地转成可收集的 pytest 骨架；
- `evidence.py` 仍是证据与 manifest 的唯一写入者；
- `run_selenium.py` 仍是执行与 JUnit 摘要的唯一写入者；
- `pre_submission_gate.py` / `package_submission.py` 负责最终质量与交付包。

流水线不调用 LLM、不自动执行这些工具（除 `block` 的 manifest 同步外），因此可以在无模型环境中独立运行和审计。

## 8. 练习 Fixture

`fixtures/cartcheck/` 是受控练习应用：

```powershell
python fixtures/cartcheck/serve.py --port 8765
# http://127.0.0.1:8765/
```

- 纯静态 HTML/CSS/原生 JS，无构建、无依赖、无网络请求；
- 需求唯一依据：`fixtures/cartcheck/REQUIREMENTS.md`（只读）；
- 代码中植入了 3 个受控缺陷，用 `SEED-DEFECT` 注释标记，页面不暴露任何提示；
- 缺陷只用于验证「能否用测试发现真实偏差」，不得当作真实产品结论。

## 9. Scaffold 契约

```powershell
python tools/scaffold.py --slug cartcheck --target http://127.0.0.1:8765/ `
  --cases reports/test-cases/cartcheck-test-cases.csv `
  --out tests/generated/cartcheck
```

- 每条 CSV 用例生成一个 `test_<case_id 小写下划线>` 函数；
- 自动带 `case_id` / `priority` / `requirement` / `method` / `case_type` 标记；
- 函数体包含 `case_ctx.set_expected(...)`、`case_ctx.step(...)`，随后
  `raise NotImplementedError(...)`（默认）或 `pytest.skip(...)`（`--allow-skip`）；
- 绝不生成 `assert True` 之类的假测试；
- 已存在文件默认拒绝覆盖，`--force` 才覆盖；
- 生成后必须能 `python -m pytest --collect-only -q <out>` 收集成功（函数数 = CSV 行数）。

模板位于 `templates/scaffold/page_object.py.tmpl` 与 `templates/scaffold/test_module.py.tmpl`。
