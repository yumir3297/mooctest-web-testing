# 第一次实测交接单

- 日期：2026-10-31
- 用途：下一次会话直接按本单启动第一次实测，不需要重新摸环境。
- 发布仓库：https://github.com/yumir3297/mooctest-web-testing

## 1. 当前结论

| 项 | 状态 |
|---|---|
| Python 运行环境 | **READY**：`python tools/env_check.py --strict` → 17 PASS / 0 WARN / 0 BLOCKED，exit 0 |
| 技术路线 | 采用 **Python**，不使用 Java；官方要求“Python / Java 选一个即可” |
| Chrome 自动更新 | 已禁用用户级 `GoogleUpdaterTaskUser157.0.8089.0{...}`，State=`Disabled` |
| PyCharm | 用户已确认本机有；项目用命令行 pytest，不依赖 PyCharm |
| 2026 官方规则 | 已整理三条官方培训视频，见 `docs/COMPETITION_RULES_2026.md` |
| GitHub 材料 | 已推送 public 仓库，已排除 `materials/`、`booook/`、驱动二进制、`node_modules`、原始 MCP 输出 |

## 2. 这台机器上已准备好的内容

### 环境

```text
Python        3.13.9
Selenium      4.51.0
pytest        9.1.1
Chrome        156.0.8078.76
ChromeDriver  156.0.8078.80（主版本 156 一致）
```

- `env_check` 的 `driver_source=PASS`，驱动 SHA-256 与 `tools/driver/DRIVER.md` 一致。
- 官方版本兼容性已用隔离环境验证：Selenium 4.49.0 + pytest 8.4.2，TodoMVC `7 passed + 1 xfailed`，证据 15/15。
- 运行记录：`RUN-20261031-OFFICIALVER-03`。

### 代码与练习目标

- `fixtures/cartcheck/`：本地练习应用（CartCheck 结算试算器）。
- `fixtures/cartcheck/serve.py`：启动命令 `python fixtures/cartcheck/serve.py --port 8765`。
- `tests/test_todomvc.py`：环境冒烟基线。
- `tests/generated/cartcheck/`：CartCheck 的 Page Object 与测试。
- `tools/`：流水线、证据、报告、门禁、导出、发布脚本。

### 文档

- `docs/COMPETITION_RULES_2026.md`：2026 赛制、评分、提交格式、环境要求。
- `docs/ENVIRONMENT.md` §9：官方要求 vs 本机实测。
- `docs/OFFICIAL_2025.md`：2025 官方格式基线。
- `docs/ACCEPTANCE_REPORT_20261031.md`：内部验收报告。
- `docs/WORKFLOW.md`：阶段与命令。
- `docs/ISOLATION_PROTOCOL.md`：题目与答案隔离协议（干净工作区、答案移出、开跑前门禁）。
- `docs/OFFICIAL_2026_VIDEO.md`：2026 视频基线三件套（docx + 脚本 zip + 截图 zip）的生成与校验。

### 证据与交付样例

| 内容 | 路径 |
|---|---|
| 官方版本回归（真实截图） | `evidence/raw/RUN-20261031-OFFICIALVER-03/` |
| CartCheck 冷启动实跑 | `evidence/raw/RUN-20261031-COLDSTART-01/` |
| 官方格式导出（一用例一张） | `official_2025/RUN-20261031-COLDSTART-01/screenshots/` |
| 交付包截图 + index.csv | `submission/RUN-20261031-COLDSTART-01/screenshots/` |

> 这些是 CartCheck 本地练习应用和 TodoMVC 基线的真实截图，不是比赛当天题目的截图。比赛题目截图要在新 run 中生成。

## 3. 新对话开始时需要提供

第一次实测必须有明确目标，至少给齐：

1. **target URL**：比赛平台/练习站点的可访问地址。
2. **requirement**：需求文档路径（本地文件）或可读取的文档链接。
3. **slug**：站点短名，用于生成 `tests/generated/<slug>/`，例如 `cartcheck`、`baidumap`。
4. **登录方式**：如果需要登录，请你在浏览器里自行登录；不要把账号密码发给我。
5. **scope**：`full`（完整闭环）或先 `quick` 做冒烟。

推荐起手式：

```text
/web-test target=<URL> requirement=<需求文档路径> slug=<slug> scope=full
```

如果使用本地 CartCheck 练习：

```text
/web-test target=http://127.0.0.1:8765/ requirement=fixtures/cartcheck/REQUIREMENTS.md slug=cartcheck scope=full
```

## 4. 实测前 60 秒检查

如果测的是 2025 旧题或本地 CartCheck，**不要在包含 `materials/参考答案` 的当前工作区直接跑**；先按 `docs/ISOLATION_PROTOCOL.md` 建干净工作区。隔离门禁：

```powershell
# 0. 干净工作区隔离检查，必须 ISOLATION_CLEAN / exit 0
python tools\isolation_check.py --workspace <clean_room> --json

# 1. 环境门禁，必须 READY / exit 0
python tools\env_check.py --strict

# 2. 如果测本地 CartCheck，启动 target 目录里的 fixture（不要在 workspace 里）
python <target_dir>\serve.py --port 8765

# 3. 确认 Chrome 更新任务仍是 Disabled
Get-ScheduledTask -TaskPath '\GoogleUser\GoogleUpdater\' | Select-Object TaskName, State
```

## 5. 实测后必须检查

```powershell
# 证据门禁
python tools\evidence.py verify --run-id <RUN_ID> --fail-on-error

# 报告
python tools\generate_report.py --run-id <RUN_ID>

# 质量门禁（G5 = 2025 布局，G6 = 2026 视频基线）
python tools\pre_submission_gate.py --run-id <RUN_ID> `
  --official-2025 official_2025\<RUN_ID> `
  --official-2026 official_2026\<RUN_ID> `
  --out qualification/gate-runs/<RUN_ID>

# 2026 视频基线三件套（docx + 脚本 zip + 截图 zip）
python tools\export_official_2026.py --run-id <RUN_ID> --app <App> `
  --cases reports\test-cases\<slug>-test-cases.csv --slug <slug> --out official_2026
python tools\export_official_2026.py --verify official_2026\<RUN_ID> --json
```

结果位置：

```text
pipeline_runs/<RUN_ID>/          阶段状态与中间产物
reports/executions/<RUN_ID>/     JUnit、report.md/html/json
evidence/raw/<RUN_ID>/           原始截图与页面源码
evidence/logs/<RUN_ID>/          执行日志
official_2026/<RUN_ID>/          2026 视频基线三件套 + manifest
```

## 6. 已知限制

1. **2026 赛题包未发布/未获取**：评分维度与提交格式来自官方培训视频，不是官方文件；最终以赛题包内《注意事项》为准。
2. **AI 使用许可未确认**：正式提交前必须确认当届规则；未确认时只能做内部演练。
3. **Java 路径未就绪**：本机 JDK 17、无 Maven；本项目选 Python，不影响当前实测。
4. **官方驱动路径本机不存在**：`C:\Program Files\Google\Chrome\Application\chromedriver.exe` 没有；本地用 `tools/driver/chromedriver.exe`，导出官方包时写回官方路径，比赛环境要再确认。
5. **Chrome 更新任务可能重建**：Chrome 重装或大版本更新后，赛前要再检查一次 `GoogleUpdater` 任务状态。
6. **当前工作区含答案**：`materials/参考答案`、历史 `reports/`、`evidence/`、`tests/generated/` 都在当前工作区；限时演练必须另建干净工作区，不能直接在当前目录跑旧题。

## 7. 相关链接

- 仓库：https://github.com/yumir3297/mooctest-web-testing
- 2026 规则：https://github.com/yumir3297/mooctest-web-testing/blob/main/docs/COMPETITION_RULES_2026.md
- 环境对照：https://github.com/yumir3297/mooctest-web-testing/blob/main/docs/ENVIRONMENT.md
- 官方版本回归证据：https://github.com/yumir3297/mooctest-web-testing/tree/main/evidence/raw/RUN-20261031-OFFICIALVER-03
