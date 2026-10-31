# mooctest-web-testing 工作流

本文件是项目级共享规范。所有 Skill、Command 与自动化脚本都应引用本文件，避免复制同一套长指令。

## 1. 目标

把 Web 应用测试任务组织成**可追溯、可恢复、可门禁**的流水线：

```text
需求输入 → 环境检查 → 知识加载 → 需求分诊 → 浏览器探索 → 用例设计 → 用例审查
→ 脚本生成 → 脚本校验 → 执行 → 失败归因 → 证据复核 → 覆盖复核
→ 报告 → 质量门禁 → 内部交付包 → 完成
```

工作流服务 2026 全国大学生软件测试大赛 Web 应用测试赛道，但默认不修改被测业务系统，也不假设 AI 辅助已被官方允许。

## 2. 阶段、执行者与产物

| 阶段 | 执行者 | 主要产物 |
|---|---|---|
| INIT | 程序（`tools/pipeline.py init`） | `pipeline_runs/<run>/state.json`、`requirement.md` |
| ENV_CHECK | 程序（`tools/env_check.py`） | `pipeline_runs/<run>/env_check.json` |
| KNOWLEDGE_LOAD | 程序（`tools/knowledge_router.py`） | `pipeline_runs/<run>/knowledge_plan.json` |
| REQUIREMENT_ANALYSIS | Agent（`test-design-methodology`） | `requirements.json`、`<slug>-requirements.md` |
| BROWSER_EXPLORATION | Agent（`browser-exploration`） | `exploration.md` + 已登记快照/截图 |
| TEST_DESIGN | Agent（`test-design-methodology` + `test-case-design`） | `<slug>-test-cases.csv/.md` |
| CASE_REVIEW | Agent | `case-review.md` |
| SCRIPT_GENERATION | Agent（`selenium-testing`）+ `tools/scaffold.py` | `tests/generated/<slug>/` |
| SCRIPT_VALIDATION | 程序（pytest 收集 + 静态检查） | `script-validation.json` |
| TEST_EXECUTION | 程序（`tools/run_selenium.py`） | `junit.xml`、`junit-summary.json`、证据 |
| FAILURE_TRIAGE | Agent | `triage.md`、缺陷记录 |
| EVIDENCE_REVIEW | 程序（`tools/evidence.py verify`） | `evidence-review.json` |
| COVERAGE_REVIEW | Agent | `coverage.md` |
| REPORT_GENERATION | 程序（`tools/generate_report.py`） | `report.md/html/json` |
| QUALITY_GATE | 程序（`tools/pre_submission_gate.py`） | `gate-report.json` |
| PACKAGE_PREPARATION | 程序（`tools/package_submission.py`） | `submission/<run>/`、`submission.zip` |
| COMPLETE | Agent | `FINAL.md` |

**分工原则**：状态推进、Schema 校验、证据哈希、覆盖计数、门禁判定由程序完成；语义分析、页面理解、测试策略、脚本编写与失败推理由 Agent 完成。不要让提示词承担可以程序化验证的检查。

## 3. 工具选择

- 浏览器探索：优先 Playwright MCP（`browser_navigate` / `browser_snapshot` / `browser_click` / `browser_fill` / `browser_screenshot`）；不可用时用 `playwright-cli`（不要直接 `open`，进程可能不返回）。
- 正式自动化：Selenium + pytest。探索只用于确认真实 DOM 与交互路径，不替代交付代码。
- 图像处理：Pillow + OpenCV（`tools/visual_diff.py`）。
- 证据与报告：`tools/evidence.py`、`tools/generate_report.py`。
- 质量门禁与打包：`tools/pre_submission_gate.py`、`tools/package_submission.py`。

### 3.1 本机实测的 MCP 行为差异（必须知道）

| 现象 | 实测 | 应对 |
|---|---|---|
| `browser_fill` 追加而非替换 | 连续 fill 会把文本拼接到已有内容后 | 填表前先清空：`browser_evaluate` 置 `value=''` 并派发 `input` 事件，或用 `browser.fill_form` |
| `browser_press("Enter")` 可能不触发表单提交 | TodoMVC 中输入框回车未新增条目 | 优先点击真实按钮；必须回车时用 `dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))` 验证一次 |
| `browser_screenshot` 需要可见标签页 | 未 focus 时报 `Screenshot needs a visible tab` | 先 `browser_tabs_focus` 再截图 |
| 截图落在 server-local 临时目录 | 返回 `C:\TempPG\opencode-browser-*\...\screenshot.jpeg` | 复制到 `evidence/raw/<run>/<case>/` 后再 `evidence.py register` |

## 4. 状态机

运行（run）：`running → passed | failed | blocked | aborted`。
用例（case）：`not-run → running → passed | failed | xfailed | blocked | skipped`。

- `passed` 必须同时有断言记录或已登记证据（`tools/evidence.py` 强制执行）。
- `failed` 表示**用例断言失败**，不自动等于产品缺陷；必须经过归因。
- `blocked` 表示**没能执行**（环境/夹具/驱动问题），不是产品缺陷，也不计入通过率。
- `xfailed` 是受控预期失败，单独统计，不计入通过率。
- 运行状态由 `tools/run_selenium.py` 与 `tests/conftest.py` 写入，不手工伪造。

## 5. 证据门禁

每个用例至少一条可追溯证据。失败用例必须有：视口截图、整页截图、页面源码、浏览器控制台日志、断言错误信息。

- 证据必须登记到 `evidence/manifest.json`，路径必须在 `evidence/<bucket>/<run_id>/` 下。
- 跨 run 引用（路径里的 RUN 与登记 run 不一致）会被拒绝；历史遗留条目由 `verify` 报出。
- 同一 run 同一路径重复登记会被拒绝。
- 原始截图只增不改；标注图、裁剪图、差异图写入 `annotated/`、`diff/`。

## 6. 截图策略

- 先 DOM/无障碍快照，后截图。
- 优先元素截图；整页截图只在布局、溢出、遮挡时使用。
- 同一状态不重复截图；截图前固定视口（1280×900）、缩放、语言、主题。
- 动态内容用 `--ignore-box` 屏蔽后再解释差异。

## 7. 失败处理与归因

失败先分类，再决定动作：

| 分类 | 判据 | 处置 |
|---|---|---|
| ENV | 驱动/浏览器/端口/网络 | 修环境后重跑，不记缺陷 |
| LOCATOR | 元素找不到、选择器失效 | 回探索阶段重新定位 |
| TIMING | 竞态、动画未结束 | 改等待条件，禁止 `time.sleep` |
| DATA | 测试数据不合法 | 修数据 |
| SCRIPT | 代码逻辑错误 | 修脚本 |
| ASSERT | 断言与需求不符 | 改断言必须引用需求原文并记录 |
| APP | 需求与实现不符且可复现 | 登记缺陷（前置/步骤/预期/实际/证据/复现状态） |
| UNKNOWN | 证据不足 | 标 `needs_review`，不得写 confirmed |

受控修复预算：每个 run 最多 3 次修复（`tools/pipeline.py record-repair`），超预算必须 `block`。

**禁止**：删除断言、无依据修改预期、跳过失败用例、把失败改成 xfail 来制造通过。

## 8. 质量门禁

`tools/pre_submission_gate.py` 输出两个独立结论：

- `test_verdict`：被测应用是否通过测试。
- `delivery_verdict`：这批测试成果是否可信、可交付。

真实产品缺陷导致 `test_verdict=FAIL`，只要缺陷已确认、记录完整并取证，`delivery_verdict` 仍可为 `PASS`。门禁拦的是「不可信的测试成果」，不是「被测系统有问题」。

退出码：`0` PASS/WARNING，`1` FAIL，`2` BLOCKED，`3` UNVERIFIED。

## 9. 效率与上下文

- 一个运行复用一个浏览器会话；用例间清理状态。
- 不把大图/完整快照塞进主上下文，只引用路径与摘要。
- 按阶段加载知识（`tools/knowledge_router.py`），不全量读取知识库。
- 同一证据只登记一次；同一状态不重复截图。

## 10. 安全与合规

- 只测试已授权目标；不扫描未授权站点。
- 不读取、上传或泄露凭据；截图前遮蔽密码、令牌、个人数据。
- 不修改被测系统业务代码；不自动提交远程仓库。
- 2026 官方 AI 使用许可**尚未确认**：本地开发、练习与自建 fixture 可以做；正式比赛环境必须另行取得授权，`/web-test --official-submission` 在未声明 `AI_USE_CONFIRMED` 时必须 BLOCKED。

## 11. 快速入口

```powershell
# 环境自检（阻塞时退出码 2）
python tools/env_check.py --json

# 知识路由（按阶段最小加载）
python tools/knowledge_router.py --list-stages
python tools/knowledge_router.py --stage test-design --json

# 新建/恢复流水线
python tools/pipeline.py init --run-id RUN-20261101-120000 --target http://127.0.0.1:8765/ `
  --requirement fixtures/cartcheck/REQUIREMENTS.md --slug cartcheck --scope full
python tools/pipeline.py resume --run-id RUN-20261101-120000

# 生成测试骨架后补全实现
python tools/scaffold.py --slug cartcheck --target http://127.0.0.1:8765/ `
  --cases reports/test-cases/cartcheck-test-cases.csv --out tests/generated/cartcheck

# 执行
python tools/run_selenium.py --run-id RUN-20261101-120000 --target http://127.0.0.1:8765/ `
  --suite tests/generated/cartcheck --capture-pass

# 证据 / 报告 / 门禁 / 打包
python tools/evidence.py verify --run-id RUN-20261101-120000 --fail-on-error
python tools/generate_report.py --run-id RUN-20261101-120000
python tools/pre_submission_gate.py --run-id RUN-20261101-120000 --out qualification/gate-runs/RUN-20261101-120000
python tools/package_submission.py --run-id RUN-20261101-120000
python tools/package_submission.py --verify submission/RUN-20261101-120000
```

统一 Agent 入口：`/web-test target=... requirement=... slug=... scope=full`、`/web-test --check`、`/web-test --resume <RUN_ID>`。
