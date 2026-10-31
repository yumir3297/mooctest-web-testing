# 工程进度与模块所有权

- 建立时间：2026-10-31
- 用途：记录本次集成任务的任务状态、依赖、写入范围、验证证据。
- 基线快照：`backups/baseline-20261031-file-hashes.txt`（481 个文件的 SHA-256，排除 `node_modules`、`__pycache__`、`.pytest_cache`）。

## 0. 基线状态（PHASE 0）

| 项 | 实际结果 |
|---|---|
| 版本控制 | `git status` → `fatal: not a git repository`。**本仓库不是 Git 仓库**，因此不能使用 worktree/分支隔离。 |
| 并行策略 | 共享文件由主 Agent 顺序修改；子 Agent 只写各自新建文件或独占文件。 |
| 未提交用户修改 | 无 VCS 可判断，改用基线哈希快照替代；任何删除/覆盖均可通过快照回查。 |
| 既有证据 | `evidence/manifest.json` 有 8 个运行、99 条证据登记。**本次任务不覆盖、不改写历史证据。** |
| 既有报告 | `reports/executions/` 5 个运行目录、`reports/test-cases/` 4 套用例文件，保持只增不改。 |

### 0.1 环境实测（2026-10-31）

| 组件 | 实测值 | 命令 |
|---|---|---|
| Python | 3.13.9 | `python --version` |
| pytest | 9.1.1 | `python -m pytest --version` |
| Selenium | 4.51.0 | `python -c "import selenium"` |
| Chrome | 156.0.8078.74 | `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe` 文件版本 |
| ChromeDriver | 155.0.8059.84 | `tools\driver\chromedriver.exe --version` |
| openpyxl | 3.1.5 | `python -c "import openpyxl"` |
| Pillow / OpenCV / numpy | 12.2.0 / 5.0.0 / 2.4.4 | `python -c "import PIL,cv2,numpy"` |
| Node.js | 24.14.1 | `node --version` |
| Playwright CLI | 0.1.22 | `npx --no-install playwright-cli --version` |

→ **P0-2 仍然存在**：Chrome 主版本 156，ChromeDriver 主版本 155。

## 1. 模块所有权（写入范围）

| 工作单元 | 独占写入范围 | 依赖 | 状态 |
|---|---|---|---|
| 主 Agent（集成） | `docs/PROGRESS.md`、`docs/ARCHITECTURE.md`、`docs/ACCEPTANCE_REPORT_20261031.md`、`tools/evidence.py`、`tests/conftest.py`、`tools/run_selenium.py`（集成期）、`opencode.json` | — | 进行中 |
| A 环境与工具链 | `tools/env_check.py`、`tools/driver/`、`requirements.txt`、`docs/ENVIRONMENT.md` | — | 待分派 |
| B 知识与 Skill | `.opencode/skills/test-design-methodology/`、`tools/knowledge_router.py`、`knowledge/`（仅 README 与 archive 标注）、`mooctest-knowledge/reports/INTEGRATION-v0.2.1.md` | — | 待分派 |
| C 质量门禁 | `tools/pre_submission_gate.py`、`tools/validators/`、`qualification/`（负向样本根目录）、`tests_meta/test_pre_submission_gate.py` | 主 Agent 的 manifest schema | 待分派 |
| D 自主测试流水线 | `tools/pipeline.py`、`fixtures/cartcheck/`、`templates/`、`pipeline_runs/` | C 的门禁 CLI、A 的环境检查 CLI | 待分派 |
| E 报告与交付 | `tools/package_submission.py`、`tools/generate_report.py`、`submission/` | 主 Agent 的 manifest schema | 待分派 |

**冲突规则**

1. `tools/evidence.py`、`tests/conftest.py` 只由主 Agent 修改；子 Agent 需要字段变更时提交需求，不直接改。
2. `tools/generate_report.py` 由 E 独占；D 只通过 CLI 调用，不 import 内部函数。
3. 子 Agent 不得写入 `evidence/raw/`、`evidence/logs/` 下已存在的运行目录。
4. 子 Agent 不得修改 TodoMVC 既有文件：`tests/test_todomvc.py`、`tests/test_todomvc_expected_failure.py`、`tests/pages/todo_page.py`。

## 2. 任务状态

| ID | 任务 | 依赖 | 验收证据 | 状态 |
|---|---|---|---|---|
| T0 | 建立基线与所有权 | — | 本节 + 基线哈希 | DONE |
| T1 | 修复 Chrome/Driver 版本漂移，环境检查硬失败 | T0 | `tools/env_check.py` 实跑、驱动版本、TodoMVC 回归 | DONE（ChromeDriver 156.0.8078.80 官方 CfT；`env_check` READY exit 0；换回 155 时 BLOCKED exit 2；回归 `RUN-20261031-ENVCHECK-01` 7 passed + 1 xfailed，15/15 证据） |
| T2 | 安装并接入 `test-design-methodology`，消除知识冲突 | T0 | `opencode debug skill`、路由实跑、BVA 冲突消解 | DONE（Skill 运行时可加载并返回 base directory；`check_refs.py` errors=0；路由 11 阶段互不相同；3 项冲突已消解并保留来源） |
| T3 | 用例/脚本/证据/缺陷分层质量门禁 + 负向样本 | T0 | `pre_submission_gate` 正负跑 | DONE（12 负向 + 2 正向样本；`tests_meta` 22 passed；真实 run 退出码与 G4 集成实测） |
| T4 | 新站点自主测试流水线与状态恢复 | T3 部分 | cold start 运行记录 | DONE（17/17 阶段，30 用例，25 passed/5 failed，5 缺陷/3 根因，83/83 证据） |
| T5 | 报告字段补全与内部交付包 | T0 | 报告 + `submission/` + zip 校验 | DONE（环境表全字段、预期不再被断言覆盖、`--verify` 24/24、zip 哈希稳定一致） |
| T6 | 端到端验收（cold start + 回归） | T1–T5 | 验收报告 | DONE（`docs/ACCEPTANCE_REPORT_20261031.md`） |
| T7 | 接入 2025 官方赛项材料（official-2025 导出 + G5 门禁） | T0 | 导出/校验实测、G5 集成、真实站点只读探测 | DONE |

## 2.1 主 Agent 已完成的共享层改动

| 文件 | 改动 | 验证 |
|---|---|---|
| `tools/evidence.py` | schema 1.1：用例级 expected/actual 与断言分离；缺陷新增 environment/preconditions/repro_steps/repro_status/category/severity_rationale；`passed` 必须有断言或证据；证据登记拒绝跨 run 与重复；`verify` 新增 cross_run/unscoped/duplicates | `verify` 复现审计提到的 9 条历史跨 run + 3 条 unscoped；`RUN-20261031-BASELINE-01` 15/15 |
| `tests/conftest.py` | 驱动主版本硬校验（不一致直接失败）；setup 失败记 `blocked` 而非产品失败；`set_expected/set_actual` 分离；环境快照写入运行 | 同上；`RUN-20261031-SCHEMA-02` 2 passed |
| `tools/run_selenium.py` | 真实环境版本采集（Chrome 156.0.8078.74 / Driver 156.0.8078.80 / Selenium 4.51.0 / pytest 9.1.1）；默认拒绝复用已完成 run；超时强杀进程树并记 blocked；运行状态按 manifest 用例分布判定 | `RUN-20261031-BASELINE-01` |
| `tools/versioning.py` | 新增：Windows 文件版本读取（`chrome.exe --version` 在 Windows 无输出） | 环境快照实测 |
| `docs/CONTRACTS.md` | 冻结模块接口契约 | — |
| `docs/coldstart/HIDDEN_EXPECTATIONS.md` | 冷启动隐藏验收基准（3 个植入缺陷 + 12 个必须覆盖点） | 冷启动前固定 |

## 2.2 已知并保留的历史数据问题（不修改历史）

- `manifest.json` 中 9 条证据登记在 `RUN-20261029-02` 名下，但文件位于 `RUN-20261029-01/` 目录（跨 run）。
- 3 条 MCP 自动输出（`evidence/raw/mcp/page-*.yml`）无 run 归属（unscoped）。
- 这两类问题是**历史事实**，新代码已能检出并阻断新增；本次不修改历史条目。

## 3. 日志

| 时间 | 事件 |
|---|---|
| 2026-10-31 | 建立基线哈希、所有权矩阵；确认仓库非 Git，改用顺序集成 + 独占文件并行。 |
| 2026-10-31 | Agent A 完成驱动 156.0.8078.80 升级与环境门禁；`env_check` READY exit 0，换回 155 时 BLOCKED exit 2。 |
| 2026-10-31 | Agent B 完成 `test-design-methodology` 安装与知识路由；Skill 运行时可加载。 |
| 2026-10-31 | 主 Agent 实跑 `/web-test --check`：输出 `WEB_TEST_READY`，退出码 0，未创建运行（`pipeline.py status` 返回 `RUN_NOT_FOUND` exit 2）。日志 `reports/tooling/RUN-20261031-CMDCHECK-01/web-test-check.log`。 |
| 2026-10-31 | 主 Agent 用 Playwright MCP 独立核验 CartCheck fixture：E1/E4/E5/E6/E7 符合、E2/E3 不符、小写券码被接受，确认 3 个植入缺陷真实存在。证据 `docs/coldstart/REFERENCE-VERIFICATION-20261031.md`。 |
| 2026-10-31 | Cold start `RUN-20261031-COLDSTART-01` 完成 17/17 阶段：30 用例、25 passed / 5 failed、5 缺陷 / 3 根因、83/83 证据、门禁全 PASS（delivery PASS / test FAIL）、交付包 89 文件 24/24。交付包在项目外独立复跑得到同样的 25 passed / 5 failed。 |
| 2026-10-31 | 修复交付包缺少 `page_*.py` 与 evidence 模块导致不可独立运行的问题；门禁 `--requirements` 增加 JSON 支持。重跑门禁与打包均通过。 |
| 2026-10-31 | 最终回归 `RUN-20261031-FINAL-REGRESSION-01`：7 passed + 1 xfailed，15/15 证据。TodoMVC 三个基线文件哈希与冷启动前一致。 |
| 2026-10-31 | 输出验收报告 `docs/ACCEPTANCE_REPORT_20261031.md`：A=PASS（本地受控）、B=PASS（运行时接入）、C=PASS（内部交付）。 |
| 2026-10-31 | 用户新增 `materials/`（8 套 2024–2025 赛题 + 5 套参考答案）。主 Agent 提取官方 2025 规范：10 列用例表、`<App>_R001_001` 编号、`<11位时间戳>_<编号>.png` 截图、一需求一函数。新增 `tools/export_official_2025.py` 与门禁 G5；冷启动 run 导出 30 用例/10 需求/30 截图，`--verify` PASS，包内 runner 独立复跑 25 passed / 5 failed。 |
| 2026-10-31 | 真实站点只读探测 `RUN-20261031-REALSITE-01`：顺丰首页可达并命中服务查询入口；知乎被重定向到登录页，按授权不登录 → 记为 `blocked`（2/2 证据）。 |
