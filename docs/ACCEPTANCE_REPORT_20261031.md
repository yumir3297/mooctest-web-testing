# AI Agent 测试系统集成验收报告

- 日期：2026-10-31
- 工作目录：`<PROJECT_ROOT>`
- 性质：正式工程实施 + 实际执行 + 端到端验收（非计划书、非只读审计）
- 判定原则：文件存在 ≠ 功能实现；实现 ≠ 可运行；可运行 ≠ 测试有效；测试有效 ≠ 交付合规

---

## 0. 结论摘要

| 目标 | 判定 | 依据（全部为实际执行） |
|---|---|---|
| **A. 全流程自主测试** | **PASS（本地受控环境）** | 从一个只有 URL + 需求文档的新站点出发，17/17 阶段自动闭环：30 条用例、25 passed / 5 failed、5 条缺陷 / 3 个根因、83 条证据、报告、门禁、交付包，全程无需为该项目手写脚本 |
| **B. 知识蒸馏与 Skills 接入** | **PASS（运行时已接入）** | `test-design-methodology` 安装到 `.opencode/skills/`，运行时可加载；11 阶段确定性路由；3 项规范冲突已消解；冷启动用例中出现 `边界值 3-value（499/500/501）` 等新口径证据 |
| **C. 质量自检与交付控制** | **PASS（内部交付）** | G0–G4 五层门禁；12 个负向样本全部被阻断；真实受阻运行 exit 2；真实产品缺陷场景 delivery=PASS / test=FAIL；交付包 24/24 校验通过且可独立复跑 |
| **正式竞赛合规** | **PARTIAL（2025 基线 + 2026 视频规则）** | 2025 官方模板、用例表、截图与代码规范已从 `materials/` 取得并完成适配（见附录 A）；2026 培训视频的评分维度、提交格式与环境要求已整理（见 `docs/COMPETITION_RULES_2026.md`）；**2026 赛题包与 AI 使用许可仍未获取**。本报告不声称符合 2026 官方完整要求 |

**内部系统集成验收：通过。**
**正式竞赛 AI 许可与官方交付格式认证：未取得，不得对外宣称。**

> 2026 视频基线提交包已生成并校验（`official_2026/RUN-20261031-COLDSTART-01`，见 `docs/OFFICIAL_2026_VIDEO.md`）；官方 2026 模板未获取，不能标为 `official-2026`。

---

## 1. 验收环境

| 项 | 值 | 来源 |
|---|---|---|
| OS | Windows 11 10.0.26340 | `platform.platform()` |
| Python | 3.13.9 | 实测 |
| Selenium | 4.51.0 | 实测 |
| pytest | 9.1.1 | 实测 |
| Chrome | 156.0.8078.74 | Windows 文件版本 |
| ChromeDriver | 156.0.8078.80 | `chromedriver.exe --version` |
| openpyxl | 3.1.5 | 实测 |
| Node | 24.14.1 | 实测 |
| OpenCode | 1.19.3 | `npx -y opencode-ai@1.19.3 --version` |
| 版本控制 | **非 Git 仓库** | `git status` → `fatal: not a git repository` |

---

## 2. PHASE 0：安全开发基线

| 项 | 实际结果 |
|---|---|
| 版本控制状态 | 目录不是 Git 仓库，**无法使用 worktree / 分支隔离** |
| 替代基线 | `backups/baseline-20261031-file-hashes.txt`：481 个文件的 SHA-256 与字节数（排除 `node_modules`、`__pycache__`、`.pytest_cache`） |
| 用户既有工作 | 未删除、未覆盖任何既有文件；旧驱动归档而非删除；历史证据与历史报告哈希保持不变 |
| 所有权矩阵 | `docs/PROGRESS.md` §1：共享文件由主 Agent 独占，子 Agent 只写独占路径 |
| 接口契约 | `docs/CONTRACTS.md`：manifest / JUnit / 用例表 / 门禁 / 交付包 / 流水线状态 六类机器可读接口 |

**并行方式**：5 个子 Agent（A 环境、B 知识、C 门禁、D 流水线、E 报告打包）并行执行互不冲突的文件；主 Agent 顺序修改 3 个共享文件（`tools/evidence.py`、`tests/conftest.py`、`tools/run_selenium.py`）。

**验收**：可追溯、无既有内容丢失、可安全并行 → **满足**。

---

## 3. PHASE 1：浏览器与执行环境（审计 P0-2）

### 3.1 问题复现

审计记录 Chrome 156 / Driver 155。本次复查确认：`env_check` 在替换前会判 `driver_major_match` 不一致。

### 3.2 修复

| 动作 | 结果 |
|---|---|
| 下载官方 Chrome for Testing | `https://storage.googleapis.com/chrome-for-testing-public/156.0.8078.80/win64/chromedriver-win64.zip`，HTTP 200 |
| 校验 | 解压后 `chromedriver.exe` 可执行；SHA-256 `95AE04AEBD7DAF845DCE58D42139F0ACBF1A5172FD480DB328EA70BDC6301790`，24,290,304 B |
| 旧驱动 | 归档至 `tools/driver/archive/chromedriver-155.0.8059.84.exe`（可回滚，未删除） |
| 版本记录 | `tools/driver/DRIVER.md`：来源 URL、哈希、平台、架构、升级/回滚步骤 |
| 启动逻辑 | `tests/conftest.py` 建立会话前做 Chrome/Driver 主版本硬校验；建立会话后再用 capability 复核一次 |

### 3.3 环境门禁（`tools/env_check.py`）

```text
[PASS] python_version / selenium / pytest / openpyxl / pillow / opencv / numpy
[PASS] chrome_binary      C:\Users\<user>\Google\Chrome\Application\chrome.exe
[PASS] chrome_version     156.0.8078.74
[PASS] chromedriver_version 156.0.8078.80
[PASS] driver_major_match chrome major 156 == driver major 156
[PASS] driver_source      sha256 matches DRIVER.md
[PASS] skills_dir         project=7 (.opencode/skills) external=5 (.agents/skills), missing=0
verdict: READY (PASS=17 WARN=0 BLOCKED=0)  exit=0
```

**负向验证（真实换文件）**：换回 155 驱动 → `driver_major_match` 与 `driver_source` 双 BLOCKED，`verdict=BLOCKED`，**exit=2**；`--strict` 下 WARN → **exit=3**。恢复 156 后复核 `READY` / exit 0。

### 3.4 浏览器通道验收

| 能力 | 结果 |
|---|---|
| Selenium 会话建立 | `browserVersion=156.0.8078.74`，`chromedriverVersion=156.0.8078.80` |
| 访问 / 输入 / 点击 / 截图 | 独立冒烟脚本实测通过（TodoMVC 新增、勾选、截图） |
| Playwright MCP | 主 Agent 会话实测：`tabs.open` → `snapshot`（含 ref）→ `fill` → 回车 → `evaluate` 读回 `1 item left` → `tabs.focus` → `screenshot` 成功 |
| MCP 已知差异 | `fill` 追加而非替换；`press("Enter")` 可能不提交；截图需先 focus 且落在 server-local 临时目录 → 已写入 `docs/WORKFLOW.md` §3.1 与 `browser-exploration` Skill |

### 3.5 回归

| 运行 | 结果 |
|---|---|
| `RUN-20261031-ENVCHECK-01` | 7 passed + 1 xfailed，exit 0，证据 15/15 |
| `RUN-20261031-BASELINE-01` | 7 passed + 1 xfailed，exit 0，证据 15/15 |
| `RUN-20261031-FINAL-REGRESSION-01` | 7 passed + 1 xfailed，exit 0，证据 15/15，21.66s |

**验收**：驱动与浏览器主版本一致；`--check` 在不兼容时非零；既有测试无退化 → **满足**。

---

## 4. PHASE 2：知识蒸馏与 Skill 接入（审计 P1-1）

### 4.1 唯一规范源

| 主题 | 唯一规范源 | 旧路径状态 |
|---|---|---|
| 方法选择 / 覆盖项 / 停止条件 | `.opencode/skills/test-design-methodology/references/method_selector.md` | `knowledge/08_derived_rules/test_design_decision_rules.md` 已加 **ARCHIVE** 横幅 |
| 预期判据 / 失败归因 | `.../references/test_oracle.md` | 同上 |
| 用例审查 / 覆盖率 | `.../references/coverage_review.md` | 同上 |
| ID 与证据命名 | `docs/CONVENTIONS.md` | `submission_schema.md` 的 `TC-WEB-xxx` / `SHOT-...` 已声明作废 |
| 规则台账 | `mooctest-knowledge/inventory/rule_registry.csv` | — |

**正文未被删除**，仅加状态横幅与取代说明，保留来源追溯。

### 4.2 三项冲突的消解

| # | 旧口径 | 现行口径 | 处理 |
|---|---|---|---|
| 1 | `knowledge/README` 推荐已归档规则 | 运行时以安装后的 Skill 为准 | README 改为归档导航 + 重定向表 |
| 2 | 边界值「每边 min-1/min/max/max+1 四点」 | `MS-01` 的 2-value / 3-value 覆盖项，禁止把 4 点当通用门禁 | 旧文件横幅逐条声明作废；台账标 `deprecated` |
| 3 | `TC-WEB-xxx` / `RUN-YYYYMMDD-01` / `SHOT-...png` | `TC-<模块>-<序号>` / `RUN-YYYYMMDD-HHMMSS` / `<case_id>__<stage>__<kind>__<UTC>.<ext>` | 旧文件声明作废；`§6 十条自动校验` 标注为历史设想 |

### 4.3 安装与可加载验证

```text
python scripts/check_refs.py  ->  errors=0, warnings=0（5 个 references + rule_registry 40 条 active）
npx -y opencode-ai@1.19.3 debug skill
  name=test-design-methodology
  location=.opencode/skills/test-design-methodology/SKILL.md
```

主 Agent 在运行时实际加载该 Skill，返回 `Base directory ... .opencode\skills\test-design-methodology` 与 6 个资源文件；说明 Skill 不是「被发现了」，而是**能被加载并解析相对路径**。

### 4.4 阶段路由（`tools/knowledge_router.py`）

- 11 个阶段，每个阶段返回 `skills / knowledge / rules / avoid / notes`，各阶段集合互不相同（2–3 个知识文件），不存在「每阶段返回全部文件」。
- 启动时校验引用路径必须存在；注入一个不存在的路径 → `[FAIL] ... EXIT=1`；非法 stage → exit 2。
- `avoid` 显式拦截 `knowledge/08_derived_rules/*` 与旧 README，并给出替代路径。

### 4.5 有效性验证

`samples` 组 A/B 同题对比（同一「优惠券结算」需求，单次、非盲评）：

| 维度 | A 组（无 Skill） | B 组（加载 Skill） |
|---|---:|---:|
| 需求分诊条数 | 0 | 17（可测 13 / 需澄清 4） |
| 显式覆盖项 | 0 | 31 |
| 用例条数 | 16 | 24 |
| 无效分区覆盖（共 13） | 9 | 13 |
| 判定表可达规则命中（共 8） | 0 | 8 |
| 不可判定预期（「正常显示」类） | 3 | 0 |
| 重复用例 | 1 | 0 |

**B 组用例更多不等于更好**：差异主要来自把 13 个无效分区和边界项拆开；边界命中只从 9 提升到 10，因为 B 组对取整口径缺失主动放弃 501/801。该试验的局限（单样本、非盲评、非真实赛题、用例全部 `NOT_RUN`）已记录在 `mooctest-knowledge/evaluations/RUNTIME_CALL_TEST-20261031.md`。

### 4.6 冷启动中的真实调用证据

冷启动生成的 30 条用例中，`method` 列出现：

```text
边界值 3-value（499/500/501）×2      边界值 3-value（799/800/801）×2
边界值 3-value（9998/9999/10000）×2   判定表（规则列 6/7/8/9）
格式边界（长度 5/6/7）                格式错误猜测（字符集/前缀）
输出边界值（0/1）+ 判定表             非功能阈值检查（MS-07）
```

即：实际使用的是 v0.2.1 的 3-value 覆盖项与判定表，**不是**已归档的四点法。

**验收**：知识可在实际工作流中被调用，规范冲突已消解，有可复核的调用测试 → **满足**。

---

## 5. PHASE 3：确定性质量门禁

### 5.1 结构

`tools/pre_submission_gate.py` + `tools/validators/`（env / cases / scripts / evidence_check / defects / package）。

| Gate | 检查重点 |
|---|---|
| G0 | 环境字段完整性、Chrome/Driver 主版本、AI 合规声明 |
| G1 | Case ID 唯一与格式、必填字段、可判定预期、步骤数、正/负/边界覆盖、需求追溯、重复 |
| G2 | AST 语法、`pytest --collect-only` 实收集、用例↔函数映射、断言存在、无 `time.sleep`、JUnit↔manifest 交叉核对 |
| G3 | 证据哈希/缺失/跨 run/重复、passed 必须有证据、failed 必须有归因或缺陷、缺陷字段完整性 |
| G4 | 交付包结构、xlsx 可打开、zip 可解压、逐文件哈希 |

**双结论**：`test_verdict`（应用是否通过测试）与 `delivery_verdict`（成果是否可信可交付）分离。

### 5.2 负向测试（`qualification/negative/`，12 个）

| 样本 | exit | delivery | 命中 |
|---|---:|---|---|
| `empty-cases` | 1 | FAIL | `CASES_EMPTY`, `REQUIREMENT_NOT_COVERED` |
| `missing-expected` | 1 | FAIL | `CASE_EXPECTED_MISSING` |
| `duplicate-case-id` | 1 | FAIL | `CASE_ID_DUPLICATE` |
| `no-boundary-coverage` | 1 | FAIL | `CASE_TYPE_COVERAGE_MISSING` |
| `no-assertion` | 1 | FAIL | `CASE_WITHOUT_ASSERTION` |
| `junit-manifest-mismatch` | 1 | FAIL | `JUNIT_MANIFEST_COUNT_MISMATCH`, `MANIFEST_PASSED_WITHOUT_JUNIT` |
| `fake-pass` | 1 | FAIL | `JUNIT_SUMMARY_MISSING` |
| `missing-screenshot` | 1 | FAIL | `PASSED_CASE_WITHOUT_EVIDENCE` |
| `bad-sha256` | 1 | FAIL | `EVIDENCE_HASH_MISMATCH` |
| `defect-no-repro` | 1 | FAIL | `DEFECT_FIELD_MISSING` |
| `blocked-run` | 2 | BLOCKED | `RUN_STATUS_BLOCKED` |
| `unverifiable-run` | 3 | UNVERIFIED | `EXECUTION_NOT_VERIFIABLE` |

### 5.3 正向测试（`qualification/positive/`）

| 样本 | delivery | test | 说明 |
|---|---|---|---|
| `defect-reported` | **PASS** | **FAIL** | 用例失败 + 字段完整已确认缺陷 → 允许交付 |
| `suspected-defect` | **WARNING** | **FAIL** | 疑似缺陷只降级为 WARNING，不自动升级 |

### 5.4 真实运行

| 运行 | exit | delivery | test | 说明 |
|---|---:|---|---|---|
| `RUN-AUDIT-20261030-02`（含 G4） | 0 | WARNING | PASS | 该 run 环境字段是旧格式，只告警；G4=PASS |
| `RUN-CMDCHECK-01`（历史受阻） | **2** | BLOCKED | BLOCKED | 修复了审计 C5「阻塞运行仍 exit 0」 |
| `RUN-20261029-02`（持有 9 条跨 run 证据） | **1** | FAIL | PASS | `EVIDENCE_CROSS_RUN`，证明检查未被放宽 |
| `RUN-20261031-COLDSTART-01` | 0 | **PASS** | **FAIL** | 5 条真实产品缺陷，全部 G0–G4 PASS |

### 5.5 门禁自测

```text
python -m pytest tests_meta -q        22 passed in 32.45s
python -m pytest tests_meta_report -q 12 passed in 6.26s
```

### 5.6 对真实交付物的注入验证

把冷启动的用例表复制一份并篡改（重复 Case ID + 把一条 expected 改成「正常显示」），用同一 run 的 JUnit 跑门禁：

```text
exit=1  delivery=FAIL  FAIL codes=['CASE_EXPECTED_VAGUE', 'CASE_ID_DUPLICATE']
```

**验收**：门禁可重复执行、正负向可区分、能区分「产品 Bug」与「成果不可信」→ **满足**。

---

## 6. PHASE 4：新站点自主测试闭环

### 6.1 解耦

- TodoMVC 保留为回归基线，`tests/test_todomvc.py`、`tests/test_todomvc_expected_failure.py`、`tests/pages/todo_page.py` 的 SHA-256 在冷启动前后**完全一致**（见 §8）。
- 新站点产物全部落在 `tests/generated/<slug>/`，与基线隔离。

### 6.2 状态机（`tools/pipeline.py`）

17 阶段，每阶段声明必须产物，`advance` 先校验再推进：

| 验证 | 实际输出 |
|---|---|
| 缺产物时 advance | `advance refused: 1 problem(s) in stage INIT` → **exit 1** |
| 重复 init | `already exists; use --force` → **exit 2** |
| 修复预算 | 第 1–3 次 exit 0；第 4 次 `repair budget exhausted` → **exit 3** |
| 中断恢复 | `resume` 输出当前阶段 / 下一步动作 / 缺失产物 / 剩余预算 → exit 0 |
| 完整 run 上 resume | `run status: complete`，`missing artifacts: (none)` → exit 0 |

### 6.3 冷启动（Cold Start Test）

**输入**（执行 Agent 只拿到这些）：URL `http://127.0.0.1:8765/` + `fixtures/cartcheck/REQUIREMENTS.md` + 运行 ID + 黑盒边界。
**未提供**：任何 CartCheck 的 Page Object、测试脚本、选择器或缺陷线索。

**受控条件**：fixture 由主 Agent 事先定义需求并植入 3 个缺陷（`docs/coldstart/HIDDEN_EXPECTATIONS.md`），主 Agent 在交付前用 Playwright MCP 独立核验过这 3 个缺陷真实存在（`docs/coldstart/REFERENCE-VERIFICATION-20261031.md`）。执行 Agent 被禁止读取 fixture 源码与隐藏预期，并在最终回复中声明「未读取」。

**执行结果**：

| 项 | 结果 |
|---|---|
| 流水线 | 17/17 阶段 done，`verify-run ok=true`，修复预算 0/3 |
| 用例 | 30 条（positive 6 / boundary 12 / negative 9 / combination 2 / nonfunctional 1） |
| 执行 | `tests=30 failures=5 errors=0 skipped=0`，36.89s，exit 1 |
| 结果分布 | passed 25 / failed 5 / blocked 0 / not-run 0 |
| 需求覆盖 | 13/13 可测需求均有用例并已执行；不可达项单独标注 |
| 证据 | 83 条，missing/mismatched/cross_run/duplicates 全 0 |
| 缺陷 | 5 条记录 / **3 个独立根因**，全部 `reproduced ×2`，各含 5 步复现、2 条前置、3 条证据 |
| 门禁 | G0–G4 全 PASS；`delivery=PASS`，`test=FAIL`，exit 0 |
| 交付包 | 89 文件，zip `0a946a02…`，`--verify` 24/24 |

**这 5 条失败对应主 Agent 植入的缺陷**：

| 用例 | 期望 → 实际 | 根因 |
|---|---|---|
| TC-CART-002 | 120/680 → 0/800 | 银卡门槛用 `> 800` 而非 `>= 800` |
| TC-CART-003 | 55/500 → 56/499 | 金卡折扣四舍五入而非向下取整 |
| TC-CART-011 | 999/8999 → 1000/8998 | 同上（9998 元） |
| TC-CART-012 | 999/9000 → 1000/8999 | 同上（9999 元） |
| TC-CART-021 | `-`/`-` + 错误提示 → 50/450 | 券码大小写校验缺失（`cp1234` 被接受） |

这 3 个根因**只从需求原文**（示例表 E2/E3、R2 的「大写」要求、R3 的「向下取整」）即可推导，无需读源码。执行 Agent 正是沿着这条路径命中，说明测试**验证了需求**而不是「验证了代码」。

### 6.4 交付包可独立复跑

把 `submission/RUN-20261031-COLDSTART-01/test-code/` 复制到项目外目录，只指向同一个 fixture 运行：

```text
5 failed, 25 passed in 28.87s
FAILED ...::test_tc_cart_002 / 003 / 011 / 012 / 021
```

与原始运行完全一致，证明交付包中的代码不是「只能看不能跑」。

**验收**：新站点可从需求 + URL 开始，经探索、生成脚本、执行、取证、报告、门禁、打包完成闭环 → **满足**。

---

## 7. PHASE 5：报告与交付包

### 7.1 修复的三个报告缺陷

| 缺陷 | 修复前 | 修复后 |
|---|---|---|
| 用例级预期被最后一次断言覆盖 | `- 预期：True` / `- 预期：False` | `见断言明细（3 条断言）` + `expected_source=assertions` + `expected_invalid=true` + 保留原值 `expected_raw` |
| 环境表缺浏览器/驱动 | 只有 python/platform/pytest/target | 运行记录含 Chrome / ChromeDriver / Selenium / Node；缺失写「未采集」，生成时探测值单列标注来源 |
| 覆盖缺口取错文件 | 引用了别的 run 的 `todomvc-test-cases.csv` | 只认 `executed_in_run` 含本 run 的用例表；找不到则显式输出 `case_table.found=false` + 原因 |

### 7.2 交付包

```text
submission/RUN-20261031-COLDSTART-01/
  test-cases.xlsx      30 行用例，16 列契约列，条件着色
  test-code/           conftest + page_cartcheck + test_cartcheck + tools/evidence.py + versioning.py
  screenshots/         72 张 PNG + index.csv
  reports/             report.md/html/json、junit.xml、junit-summary.json、pytest-console.log
  manifest.json        逐文件 sha256 + case_id + source，official_format_confirmed=false
  submission.zip       稳定 zip（固定条目时间戳）
```

| 校验 | 结果 |
|---|---|
| `--verify` | **24/24 checks PASS**，exit 0 |
| 重复生成 zip | 字节一致（`0a946a02...` → 同一哈希） |
| xlsx 行数 | 30 = manifest 用例数 |
| 用例↔代码关联 | implemented 30 / not_implemented 0 / broken 0 |
| 独立复跑 | 25 passed / 5 failed，与原始一致 |

**明确声明**：`official_format_confirmed: false`，包内 README 与 manifest 均写「内部演练交付包，2026 官方提交格式未确认」。不声称符合官方格式。

---

## 8. 回归测试结果汇总

| 回归项 | 命令 | 结果 | 证据 |
|---|---|---|---|
| 原 TodoMVC 回归 | `run_selenium.py --suite tests/test_todomvc.py --suite tests/test_todomvc_expected_failure.py` | 7 passed + 1 xfailed，exit 0 | `reports/executions/RUN-20261031-FINAL-REGRESSION-01/` |
| 证据完整性 | `evidence.py verify --run-id ...` | 15/15 | 同上；冷启动 83/83 |
| 新站点冷启动 | 见 §6.3 | 25 passed / 5 failed / 30 cases | `reports/executions/RUN-20261031-COLDSTART-01/` |
| 门禁正向 | `qualification/positive/*` | delivery PASS / WARNING | `qualification/gate-runs/positive-*` |
| 门禁负向 | `qualification/negative/*`（12 个） | exit 1 / 2 / 3 | `qualification/gate-runs/qualification-summary.json` |
| 门禁自测 | `pytest tests_meta` | 22 passed | 实测 |
| 报告/打包自测 | `pytest tests_meta_report` | 12 passed | 实测 |
| 交付包完整性 | `package_submission --verify` | 24/24 | `submission/RUN-20261031-COLDSTART-01/` |
| 基线文件未被改动 | SHA-256 对比 | 3 个 TodoMVC 文件哈希一致 | 见下表 |

```text
tests/test_todomvc.py                  10C86BDE5FBAD23005B6A516D5ADCF5D4D139E0088185EB502D6061461C775ED
tests/test_todomvc_expected_failure.py C069B6DC20E32670175CB5D563BDFE4C75D61BE3739826D9C2078E77A8B09D88
tests/pages/todo_page.py               A27ECD56B8AE7CE545ADACE4F6A8A247EA42B75C0078EC545BB1801A57814B20
（冷启动前后一致）
```

---

## 9. 冷启动七项能力判定

| 能力 | 判定 | 依据 |
|---|---|---|
| 1. 自主性 | **PASS** | 冷启动前 `tests/generated/` 不存在、无 CartCheck Page Object；30 条用例与 Page Object 由执行 Agent 生成 |
| 2. 有效性 | **PASS** | 13/13 可测需求覆盖；5 条失败全部来自需求示例与规则原文，不是「执行成功」 |
| 3. 正确性 | **PASS** | 5 条失败全部归因 `APP`；0 条误判为 `ENV/SCRIPT`；每条缺陷带 5 步复现、2 条前置、3 条证据、`reproduced×2` |
| 4. 完整性 | **PASS** | 17/17 阶段 → 报告 → 门禁 → 包 → `--verify`；用例↔代码↔截图↔结果均可追溯 |
| 5. 可恢复性 | **PASS（受控）** | 状态落在 `pipeline_runs/<run>/state.json`；`resume` 在中断态给出下一步与缺失产物（D 实测），在完整态返回 `complete`（主 Agent 实测）。**未在冷启动中途真实断电/中断后恢复** |
| 6. 质量控制 | **PASS** | 12 个负向样本被阻断；对真实交付物注入「重复 Case ID + 不可判定预期」→ exit 1 |
| 7. 可迁移性 | **PASS** | TodoMVC 三个文件哈希不变，新站点产物全部隔离在 `tests/generated/cartcheck/` |

---

## 10. 未完成事项与阻塞

| # | 项 | 状态 | 原因 / 影响 |
|---|---|---|---|
| 1 | 2026 官方评分细则 | **BLOCKED** | 官方未发布；无法核对分值、用例数上限、命名规则 |
| 2 | 2026 官方提交格式（Excel 列、压缩包结构） | **UNVERIFIED** | 交付包只能标 `official_format_confirmed=false` |
| 3 | AI 辅助/自动化的竞赛许可 | **UNVERIFIED** | 三份官方材料均未提及；`--official-submission` 在未声明 `AI_USE_CONFIRMED` 时 BLOCKED |
| 4 | 慕测平台接入（登录、题库、提交） | **BLOCKED** | 未做任何未授权访问；正式环境操作需单独授权 |
| 5 | 真实公开赛题（如顺丰练习题） | **NOT AVAILABLE** | 仓库内无该材料；冷启动使用自建 fixture |
| 6 | 浏览器矩阵 / 移动端 / 并发 / 性能阈值 | **OUT OF SCOPE** | 需求 §6 明确列为非目标，未伪造结果 |
| 7 | 冷启动中途强制中断后的恢复 | **PARTIAL** | `resume` 逻辑与状态持久化已实测，但未做「杀进程 → 重启会话 → 恢复」的破坏性演练 |
| 8 | 草案目录与安装副本的漂移检测 | **PARTIAL** | `mooctest-knowledge/skill-drafts/` 与 `.opencode/skills/` 目前只有文档约束，无自动 diff 门禁 |
| 9 | `EXPLORE` 证据容器 | **COSMETIC** | 探索证据登记在 `case_id=EXPLORE`，在 manifest 中形成一条 `not-run` 用例；不影响统计与门禁，但报告里会多一行 |
| 10 | 5 条产品缺陷的修复验证 | **NOT DONE** | fixture 是受控练习应用，缺陷为有意植入；不做修复回归 |

---

## 11. 复现命令

```powershell
# 0) 环境
python tools/env_check.py --json ; echo "exit=$LASTEXITCODE"

# 1) 知识路由与 Skill
python tools/knowledge_router.py --list-stages
python tools/knowledge_router.py --stage test-design --json

# 2) TodoMVC 回归
python tools/run_selenium.py --run-id RUN-<新ID> --target https://demo.playwright.dev/todomvc `
  --suite tests/test_todomvc.py --suite tests/test_todomvc_expected_failure.py --capture-pass
python tools/evidence.py verify --run-id RUN-<新ID> --fail-on-error

# 3) 冷启动（fixture）
python fixtures/cartcheck/serve.py --port 8765
python tools/pipeline.py init --run-id RUN-<新ID> --target http://127.0.0.1:8765/ `
  --requirement fixtures/cartcheck/REQUIREMENTS.md --slug cartcheck --scope full
python tools/pipeline.py resume --run-id RUN-<新ID>
#   …按 /web-test 的 C 节逐阶段执行…

# 4) 门禁与打包
python tools/pre_submission_gate.py --run-id RUN-<新ID> `
  --cases reports/test-cases/cartcheck-test-cases.csv `
  --junit-summary reports/executions/RUN-<新ID>/junit-summary.json `
  --requirements pipeline_runs/RUN-<新ID>/requirements.json `
  --submission submission/RUN-<新ID> --out qualification/gate-runs/RUN-<新ID>
python tools/package_submission.py --run-id RUN-<新ID> --json
python tools/package_submission.py --verify submission/RUN-<新ID> --json

# 5) 自测
python -m pytest tests_meta -q
python -m pytest tests_meta_report -q
```

---

## 12. 合规与边界声明

- 未修改任何被测系统业务代码；`fixtures/` 为本次自建的练习应用，缺陷为有意植入并已在隐藏基准中登记。
- 未访问慕测平台、未登录、未绕过任何认证或验证码、未提交任何比赛结果。
- 未删除历史证据、未覆盖原始截图、未修改历史 manifest 条目。已知的 9 条跨 run 与 3 条无归属证据为历史事实，新代码可检出并阻断新增，本次未改写。
- 所有 PASS 都附有可执行命令与产物路径；未执行的场景显式标为 `NOT RUN` / `BLOCKED` / `UNVERIFIED`。
- 内部系统集成验收通过 ≠ 已获得正式竞赛 AI 使用许可或官方交付格式认证。

---

# 附录 A：2025 官方材料接入（2026-10-31 追加）

## A.1 新增材料

用户于本日向 `materials/` 加入：

| 路径 | 内容 |
|---|---|
| `materials/赛题/` | 8 个赛项包（2024–2025）：需求文档、功能说明手册、【测试用例/测试代码/测试截图】注意事项、`测试用例模版.xlsx`、官方代码骨架 |
| `materials/参考答案/` | 5 个 2025 参考答案：Java 实现、用例模版、screenshots（10–27 张/套） |
| `materials/_原始压缩包/` | 2 个原始 zip |
| `materials/INDEX.md` | 用户整理的索引 |

这批材料把审计中「无真实赛题 / 无官方用例表 / 无官方截图规范」三项缺口变成了可核实事实。

## A.2 官方 2025 规范（三方交叉核实）

| 项 | 官方要求 |
|---|---|
| 用例编号 | `<App>_R<需求号3位>_<序号3位>`，如 `SF_R001_001`，严格区分大小写 |
| 用例表 | 10 列：测试用例编号 / 模块名称 / 需求编号 / 用例说明 / 前置条件 / 执行步骤 / 输入数据 / 预期结果 / 实际结果 / 截图文件名 |
| 截图 | 整个浏览器窗口，命名 `<11位时间戳>_<用例编号>.png`，全部放 `screenshots/`，zip 打包（禁止 rar），一条用例只留一张 |
| 代码 | 官方模板，只写 `test-code-start` / `test-code-end` 之间；**一个需求一个函数** `test_<App>_R<req>()`；`take_screenshot` 不得修改；UTF-8 |

完整对照见 `docs/OFFICIAL_2025.md`。

## A.3 与内部约定的 4 处冲突及处理

| 项 | 官方 | 内部 | 处理 |
|---|---|---|---|
| 用例编号 | `<App>_R001_001` | `TC-CART-001` | 导出时映射，内部不变 |
| 用例表 | 10 列中文 | 16 列机器可读 | 导出生成官方表，内部 CSV 仍是事实源 |
| 截图命名 | `<11位时间戳>_<编号>.png` | `<case>__<stage>__<kind>__<UTC>.png` | 导出复制重命名，原图不动 |
| 代码结构 | 一需求一函数 | 一用例一函数 + 断言 | 导出官方骨架，另附 `test-code/runner/` 可运行实现 |

## A.4 新增实现

| 文件 | 作用 |
|---|---|
| `tools/export_official_2025.py` | 导出官方 10 列 xlsx + `screenshots/` + `screenshots.zip` + `Test<App>.py` 骨架 + `manifest.json`；`--verify` 做结构门禁 |
| `tools/pre_submission_gate.py` | 新增 **G5**：`--official-2025 <dir>` 时校验官方布局；未提供则 SKIP |
| `docs/OFFICIAL_2025.md` | 规范原文提炼、差异表、用法、限制 |

## A.5 实测结果

导出 `RUN-20261031-COLDSTART-01`（CartCheck）：

```text
case_count=30  requirement_count=10  screenshot_count=30  missing_screenshots=0
official_format_confirmed=2025-baseline-only
```

| 校验 | 结果 |
|---|---|
| `export_official_2025.py --verify` | `ok=true`，FAIL=0，WARNING=1（`MULTI_REQUIREMENT_NARROWED`：24 条内部用例回指多个需求，只保留第一个） |
| 门禁 G5 | `G5=WARNING`，`delivery_verdict=WARNING`，`test_verdict=FAIL`，exit 0 |
| 包内 runner 独立复跑 | 项目外目录运行 → `5 failed, 25 passed`，与原始一致 |
| 回归 | `tests_meta` 22 passed、`tests_meta_report` 12 passed（GATES 增加 G5 后未退化） |

## A.6 真实站点只读探测（`RUN-20261031-REALSITE-01`）

按用户授权，只访问公开首页、不登录、不提交、不下单：

| 站点 | 结果 | 证据 |
|---|---|---|
| `https://www.sf-express.com/` | 可达，title「顺丰官网\|一路相伴 不负所托」，命中「服务支持 / 服务查询 / 运费时效」入口；“收寄标准”需进入子页 | `evidence/raw/RUN-20261031-REALSITE-01/PROBE/sf__home__viewport__...png` |
| `https://www.zhihu.com/` | 被重定向到 `/signin?next=%2F`，**登录墙**；按授权边界不登录，无法进入「写文章」等被测功能 | 同目录 `zhihu__home__viewport__...png` |

运行状态记为 `blocked`（2/2 证据校验通过），原因写明「只读边界内不能完成赛题功能验证」。

**结论**：顺丰类公开查询功能可在只读授权下验证；知乎类需要账号的功能必须另行取得测试账号与授权，不能用匿名访问替代。

## A.7 对既有判定的影响

| 原判定 | 更新后 |
|---|---|
| C 目标「官方格式未确认」= UNVERIFIED | **2025 基线已适配并实测**；2026 仍未确认 |
| 审计 P0-3「无 Excel / 无截图 zip / 无官方目录」 | 已实现官方 2025 布局导出与 G5 门禁 |
| 「无真实赛题」 | 已有 8 套 2024–2025 赛题与 5 套参考答案 |
| AI 使用许可 | 仍未确认，不变 |

## A.8 新增限制

1. **多需求归属**：内部用例可回指多个需求，官方一行只能填一个；当前取第一个并告警。
2. **代码骨架非成品**：`Test<App>.py` 只保证结构合规，业务步骤需补全；可运行实现另附。
3. **官方参考实现 0 断言**：官方评分更依赖截图 + 人工复核；本项目仍保留断言以保证「测试有效」。
4. **2026 模板可能变化**：若列定义或截图规则调整，需重新适配。
