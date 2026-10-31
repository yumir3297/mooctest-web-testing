---
description: Web 自动化测试闭环：需求→知识→用例→探索→Selenium→取证→门禁→报告→交付包
agent: build
---

目标：$ARGUMENTS

先读 `AGENTS.md`、`docs/WORKFLOW.md`、`docs/CONVENTIONS.md`、`docs/CONTRACTS.md`。

## 参数

| 参数 | 说明 |
|---|---|
| `target=<URL>` | 被测站点。完整执行必填 |
| `requirement=<path>` | 需求/赛题说明。缺失时必须先在 `pipeline_runs/<run>/requirement.md` 写明「假设与缺口」，不得凭空补业务规则 |
| `run_id=<RUN-...>` | 运行 ID。缺省用 `RUN-YYYYMMDD-HHMMSS` |
| `slug=<name>` | 目标站点短名，用于用例文件名与 `tests/generated/<slug>/`。**不得与既有 slug 冲突** |
| `scope=smoke\|full` | smoke 只做核心路径；full 做完整设计与执行 |
| `--check` | 只做环境/知识/依赖就绪检查，不访问目标、不建运行、不执行测试 |
| `--resume <RUN_ID>` | 从持久化状态恢复，不重新开始 |
| `--official-submission` | 声明目标是正式提交。此模式要求 `AI_USE_CONFIRMED` 已确认，否则直接 BLOCKED |
| `--authorized <note>` | 记录测试授权来源（练习环境/自建 fixture/书面许可） |

## 模式判断（先做，不可跳）

1. 参数含 `--check` → 只执行 A 节，输出结论后**停止**。
2. 参数含 `--resume` → 只执行 B 节，输出恢复点后**停止**（除非用户同时给出继续指令）。
3. 其他 → 执行 C 节完整流程。

---

## A. `--check` 模式

按顺序真实执行：

1. `python tools/env_check.py --json` → 解析 `verdict` 与退出码。
2. `python tools/knowledge_router.py --list-stages`（校验知识路由表完整）。
3. `python tools/knowledge_router.py --stage test-design --json`（确认测试设计阶段能解析到真实文件）。
4. 检查 7 个项目 Skill 与 `test-design-methodology` 是否可发现：
   `npx -y opencode-ai@1.19.3 debug skill`（过滤 name）。
5. 若给了 `run_id`：`python tools/pipeline.py status --run-id <run_id> --json`；不存在则输出 `RUN_NOT_FOUND`，不得声称已创建。

输出规则（必须二选一，不得含糊）：

- 全部 PASS → 打印 `WEB_TEST_READY`，退出码 0。
- 存在 WARN 但无 BLOCKED → 打印 `WEB_TEST_READY_WITH_WARNINGS` 并列出每条 WARN，退出码 0。
- 存在任一 BLOCKED → 打印 `WEB_TEST_BLOCKED` 并列出阻塞项，**退出码 2**。

**禁止**：在 Chrome 与 ChromeDriver 主版本不一致、驱动哈希不符、Selenium 无法导入的情况下输出 `WEB_TEST_READY`。

---

## B. `--resume` 模式

1. `python tools/pipeline.py resume --run-id <RUN_ID>`
2. 读取其输出的「当前阶段 / 缺失产物 / 修复预算」。
3. 只补做缺失产物对应的阶段；**不得重跑已完成阶段**，除非用户明确要求或产物已失效。
4. 报告恢复点、缺失项、下一步动作，然后按 C 节从当前阶段继续（若用户要求继续）。

---

## C. 完整执行模式

用 `tools/pipeline.py` 作为确定性状态机。每个阶段结束都要 `advance`，**产物不齐不得推进**。

### C0 初始化

```powershell
python tools/pipeline.py init --run-id <RUN_ID> --target <URL> `
  --requirement <PATH> --slug <SLUG> --scope <smoke|full> `
  --authorized "<授权说明>" [--official-submission]
```

- 若 `--official-submission` 且未声明 `AI_USE_CONFIRMED`：直接 `python tools/pipeline.py block --run-id <RUN_ID> --reason "AI 使用许可未确认"`，**停止**，不得继续执行正式提交产物。
- 不得复用已存在的 run_id 掩盖历史失败；要重跑就新建 run。

### C1 ENV_CHECK

```powershell
python tools/env_check.py --json > pipeline_runs/<RUN_ID>/env_check.json
```

`verdict=BLOCKED` → `pipeline.py block`，停止。不得在阻塞环境里继续跑测试。

### C2 KNOWLEDGE_LOAD

```powershell
python tools/knowledge_router.py --stage requirement-analysis --json > pipeline_runs/<RUN_ID>/knowledge_plan.json
```

按路由结果**只加载**该阶段需要的 Skill 与知识文件。
- 需求分析与方法选择：`test-design-methodology`
- 用例结构落盘：`test-case-design`
- 浏览器探索：`browser-exploration`
- 脚本实现：`selenium-testing`
- 视觉取证：`visual-testing`
- 报告：`test-reporting`

**禁止**引用 `knowledge/08_derived_rules/` 的旧规则（已归档）：边界值不得再用「每边 min-1/min/max/max+1 四点」，改用 2-value/3-value 覆盖项；ID/截图命名以 `docs/CONVENTIONS.md` 为准。

### C3 REQUIREMENT_ANALYSIS

加载 `test-design-methodology`，先做需求分诊（`可测 / 需澄清 / 不可执行 / 非测试范围`）。

产出：
- `pipeline_runs/<RUN_ID>/requirements.json`（id, text, source, status, constraint）
- `reports/test-cases/<SLUG>-requirements.md`

**规则**：`需澄清` 不得直接改判为 `可测`；无 Oracle 的行为只能记为 `NEEDS_ORACLE`，不得编造预期。

### C4 BROWSER_EXPLORATION

加载 `browser-exploration`。优先用 Playwright MCP（`browser_navigate` / `browser_snapshot` / `browser_click` / `browser_type` / `browser_take_screenshot`）；MCP 不可用再退回 `playwright-cli`（不要直接 `open`）。

- 先快照后截图；优先元素定位；记录稳定选择器。
- 产出 `reports/executions/<RUN_ID>/exploration.md`：页面、元素、选择器、交互路径、控制台错误、未覆盖路径。
- 快照/截图必须 `evidence.py register` 登记，路径必须在 `evidence/raw/<RUN_ID>/` 下；**未登记证据不得在报告中引用**。
- 只访问 `target` 指定的授权范围；不做漏洞扫描、不绕过登录/验证码。

### C5 TEST_DESIGN

加载 `test-design-methodology` + `test-case-design`。按覆盖项设计，不按用例数量。

产出（列名必须符合 `docs/CONTRACTS.md` §3）：
- `reports/test-cases/<SLUG>-test-cases.csv`
- `reports/test-cases/<SLUG>-test-cases.md`

硬要求：
- 至少 1 条 `positive`、1 条 `negative`、1 条 `boundary`。
- 每条用例 `expected` 必须是可观察值（数字/文本/URL/计数），禁用「正常显示」「功能正常」。
- 每条用例 `requirement_ids` 回指 `REQ-xx`。
- 不编造需求中不存在的业务规则；缺失信息写进 `notes` 与缺口清单。
- 不可达的测试点（例如规则下不可能出现的取值）标记为「不可达/不适用」，**不得**为了凑数编造。

### C6 CASE_REVIEW

自审并按覆盖项核对，产出 `pipeline_runs/<RUN_ID>/case-review.md`：
- 重复用例（同分区换值不算新用例）
- 缺 Oracle / 不可判定预期
- 需求无对应用例
- 边界覆盖项是否在页面上真实可表示

发现问题**回到 C5 修用例**，不要在脚本里用宽松断言绕过去。

### C7 SCRIPT_GENERATION

```powershell
python tools/scaffold.py --slug <SLUG> --target <URL> `
  --cases reports/test-cases/<SLUG>-test-cases.csv `
  --out tests/generated/<SLUG>
```

然后**由你补全** Page Object 与每条测试的真实动作与断言：

- 只用探索阶段验证过的选择器；不猜选择器。
- 显式等待（`WebDriverWait` / `expected_conditions`），**禁止** `time.sleep`。
- 断言绑定业务可观察状态（金额、计数、文本、URL）。
- 每条用例 `@pytest.mark.case_id("<ID>")`，并调用 `case_ctx.set_expected("<需求预期>")`。
- 失败用例必须能区分「产品缺陷」与「脚本/环境问题」。
- **不得**复用 TodoMVC 的 Page Object；`tests/test_todomvc.py`、`tests/pages/todo_page.py` 保持不动。

### C8 SCRIPT_VALIDATION

```powershell
python -m pytest --collect-only -q tests/generated/<SLUG>
```

产出 `pipeline_runs/<RUN_ID>/script-validation.json`（收集数、用例数、缺失映射、静态检查结果）。
收集失败或函数数 < CSV 用例数 → 回到 C7，**不得**进入执行。

### C9 TEST_EXECUTION

```powershell
python tools/run_selenium.py --run-id <RUN_ID> --target <URL> `
  --suite tests/generated/<SLUG> --capture-pass
```

- 只跑本次生成的套件，不跑 TodoMVC（除非做回归）。
- 读 `reports/executions/<RUN_ID>/junit-summary.json` 与 `evidence/logs/<RUN_ID>/pytest-console.log`。

### C10 FAILURE_TRIAGE

每个失败用例**先分类再动手**，产出 `pipeline_runs/<RUN_ID>/triage.md`：

| 分类 | 判据 | 处置 |
|---|---|---|
| ENV | 驱动/浏览器/网络/端口 | 修环境，重跑；不得记为产品缺陷 |
| LOCATOR | 元素找不到/选择器失效 | 回 C4 重新探索 |
| TIMING | 竞态、动画未结束 | 改等待条件，不用 sleep |
| DATA | 测试数据不合法 | 修数据 |
| SCRIPT | 代码逻辑错误 | 修脚本 |
| ASSERT | 断言写错（预期与需求不符） | **改断言必须引用需求原文**，并记录修订 |
| APP | 需求与实现不符，可复现 | 登记缺陷（含前置、步骤、预期、实际、证据、复现状态） |
| UNKNOWN | 证据不足 | 标记 `needs_review`，不得写成 confirmed |

受控修复预算：`python tools/pipeline.py record-repair ...`，**每个 run 最多 3 次**。超预算必须 `pipeline.py block`，不得无限重试。

**绝对禁止**：删除断言、放宽预期、跳过失败用例、把失败改成 xfail 来制造通过。

### C11 EVIDENCE_REVIEW

```powershell
python tools/evidence.py verify --run-id <RUN_ID> --fail-on-error > pipeline_runs/<RUN_ID>/evidence-review.json
```

- `missing` / `mismatched` / `cross_run` 必须为 0。
- 每个 `passed` 用例至少 1 条已登记证据。
- 失败用例必须有视口截图、页面源码、浏览器日志。

### C12 COVERAGE_REVIEW

产出 `pipeline_runs/<RUN_ID>/coverage.md`：需求 → 用例 → 执行结果 → 证据 的映射；列出未覆盖需求、未执行用例、不可达项与原因。**未执行不得写成通过。**

### C13 REPORT_GENERATION

```powershell
python tools/generate_report.py --run-id <RUN_ID> --title "<标题>"
```

报告必须含：环境（含浏览器/驱动）、范围、方法分布、用例与结果、需求覆盖、缺陷与证据、未执行项、已知限制。

### C14 QUALITY_GATE

```powershell
python tools/pre_submission_gate.py --run-id <RUN_ID> `
  --cases reports/test-cases/<SLUG>-test-cases.csv `
  --junit-summary reports/executions/<RUN_ID>/junit-summary.json `
  --requirements pipeline_runs/<RUN_ID>/requirements.json `
  --submission submission/<RUN_ID> `
  --out qualification/gate-runs/<RUN_ID>
```

`--requirements` 接受 `requirements.json`（`[{ "id": "REQ-01", ... }]`）、CSV（含 `requirement_id` 列）或纯文本。未提供时需求追溯检查降级为 WARNING。

读 `gate-report.json`：
- `delivery_verdict ∈ {PASS, WARNING}` → 可继续打包。
- `delivery_verdict = FAIL/BLOCKED/UNVERIFIED` → 回到对应阶段修复，**不得打包**。

**重要区分**：真实产品缺陷导致 `test_verdict=FAIL`，只要缺陷已确认并取证，`delivery_verdict` 仍可为 `PASS`。门禁拦的是「不可信的测试成果」，不是「被测系统有问题」。

### C15 PACKAGE_PREPARATION

```powershell
python tools/package_submission.py --run-id <RUN_ID> --cases reports/test-cases/<SLUG>-test-cases.csv --json
python tools/package_submission.py --verify submission/<RUN_ID> --json
```

- 先把 `--cases` 指向本次运行的用例表；指向的测试文件若在 `tests/generated/<slug>/` 下，包会自动带上同目录的 `page_*.py`，并附带 `tools/evidence.py` / `tools/versioning.py`，使包内代码可独立运行。
- 交付包标记为**内部演练包**（`official_format_confirmed=false`）。
- 2026 官方提交格式未确认前，不得声称符合官方要求；正式上传需单独授权。

### C15.5 官方 2025 布局导出（比赛交付时必做）

```powershell
python tools/export_official_2025.py --run-id <RUN_ID> --app <App> `
  --cases reports/test-cases/<SLUG>-test-cases.csv --module "<模块名>" `
  --with-runner --out official_2025
python tools/export_official_2025.py --verify official_2025/<RUN_ID> --json
```

- 依据 2025 赛题包：10 列用例表、`<App>_R<req>_<seq>` 编号、`<11位时间戳>_<编号>.png` 截图、`screenshots/` + zip、官方代码骨架（一个需求一个函数）。
- 再把 `--official-2025 official_2025/<RUN_ID>` 传给质量门禁，启用 **G5** 校验。
- 这是 **2025 基线**；2026 规则未确认时，只能说「按 2025 模板导出」，不能说「符合 2026 官方要求」。

### C16 COMPLETE

写 `pipeline_runs/<RUN_ID>/FINAL.md`：运行结论、用例统计（passed/failed/xfailed/blocked）、缺陷清单、覆盖缺口、门禁结论、证据路径、剩余限制。然后 `pipeline.py advance` 到 `COMPLETE`。

---

## 门禁（贯穿全程）

- 环境 BLOCKED 不得执行测试。
- 需求未确认不得写真自动化断言。
- 未验证的选择器不得写进脚本。
- 没有 JUnit 或没有证据，不得声明通过。
- 未执行 / 不可达，不得计为通过。
- 产品缺陷与测试系统故障必须分开陈述。
- 不修改被测系统业务代码；不自动提交远程仓库。
- AI 使用许可未确认前，不把本流程用于正式比赛提交。
