# OpenCode 软件测试环境部署与验收报告

- 报告日期：2026-10-29
- 项目目录：`<PROJECT_ROOT>`
- 验收运行：`RUN-20261029-02`
- 验收目标：`https://demo.playwright.dev/todomvc`
- 结论：基础设施已真实安装、配置并完成端到端验收；存在明确的能力边界与未覆盖场景，详见第 5 节。

## 1. 环境信息

| 项目 | 实测值 |
|---|---|
| 操作系统 | Windows 11 家庭版 Insider Preview，10.0.26340 |
| CPU/架构 | AMD Ryzen 7 6800H，AMD64 |
| Shell | Windows PowerShell 5.1.26100.9596 |
| 工作目录 | `<PROJECT_ROOT>` |
| OpenCode | Desktop 1.19.3（Electron 42.3.3，`E:\OpenCode\OpenCode.exe`） |
| OpenCode 配置体系 | V1（`opencode.ai/config.json`；`.opencode/skills`、`.opencode/commands`）；未升级 V2 |
| 全局配置 | `C:\Users\<user>\.config\opencode\opencode.jsonc`（未修改） |
| 项目配置 | `<PROJECT_ROOT>\opencode.json` |
| 当前模型 | `deepseek/deepseek-flash`（DeepSeek V4.1 Flash 1017） |
| 模型图像能力 | 元数据 `attachment=true`、输入模态含 image；已用截图实测通过 |
| Node.js | v24.14.1 |
| npm / npx | 11.11.0 / 11.11.0 |
| Python | 3.13.9（`C:\Users\<user>\AppData\Local\Programs\Python\Python313\python.exe`） |
| pip | 25.2 |
| Git | 2.53.0.windows.2 |
| Chrome | 155.0.8059.86 |
| Edge | 157.0.4341.24（已安装，未用于本次自动化） |
| ChromeDriver | 155.0.8059.84（`tools\driver\chromedriver.exe`） |
| Selenium | 4.51.0 |
| pytest | 9.1.1 |
| Pillow | 12.2.0 |
| OpenCV | 5.0.0.93 |
| numpy | 2.4.4 |
| Playwright CLI | 0.1.22（npm `@playwright/cli`） |
| Playwright MCP | 0.0.83（npm `@playwright/mcp`） |
| MCP 服务端 | Playwright 1.64.0-alpha-1790635538000，协议 2025-06-18，25 个工具 |
| OpenCode CLI | `opencode-ai@1.19.3`（通过 `npx` 调用，未全局安装） |
| 浏览器自动化服务 | 未发现 9222 CDP 服务；Playwright CLI 可用；Playwright MCP 当前已连接（`enabled: true`） |

### 1.1 修改前状态

- 已有 5 个项目 Skill：`test-case-writing`、`test-case-reviewer`、`ui-test-selenium`、`breakdown-test`、`playwright-cli`。
- 已有 Python 依赖：Selenium、pytest、Pillow、OpenCV、numpy、Playwright 1.61.0。
- 已有 Chrome 155 与 chromedriver 155（在 `C:\TempPG\chromedriver`）。
- 没有项目级 `opencode.json`，没有项目级 `.opencode/commands`，没有 MCP。
- 没有自定义 Agent；本次也未新建自定义 Agent，避免重复配置。

### 1.2 配置备份

- 全局配置备份：`C:\TempPG\opencode-config-backup\opencode.jsonc.20261029.bak`（含凭据，放在项目外；未将凭据内容写入项目或报告）。
- 项目依赖备份：`backups\package.json.bak`、`backups\package-lock.json.bak`。
- 未修改全局配置；项目配置只新增 MCP 段，全局模型/Provider 继续生效。

## 2. 安装组件清单

| 组件 | 版本 | 来源 | 安装位置 | 实际用途 | 功能验证 |
|---|---|---|---|---|---|
| Playwright CLI | 0.1.22 | Microsoft 官方 npm `@playwright/cli`，https://github.com/microsoft/playwright-cli | `node_modules\@playwright\cli` | 浏览器探索、无障碍快照、交互、截图 | 通过：打开 TodoMVC、快照、输入、截图 |
| Playwright MCP | 0.0.83 | Microsoft 官方 npm `@playwright/mcp`，https://github.com/microsoft/playwright-mcp | `node_modules\@playwright\mcp` | 可选 MCP 浏览器通道 | 通过：独立 MCP 客户端调用 navigate/snapshot/screenshot，25 工具 |
| ChromeDriver | 155.0.8059.84 | Chrome for Testing（先前下载，本次固定到项目） | `tools\driver\chromedriver.exe` | Selenium 驱动 | 通过：8 条 pytest 用例全部启动成功 |
| Selenium | 4.51.0 | PyPI 官方包（已存在） | Python site-packages | WebDriver 自动化 | 通过：7 条功能用例 + 1 条受控失败 |
| pytest | 9.1.1 | PyPI 官方包（已存在） | Python site-packages | 测试执行、JUnit、失败钩子 | 通过：JUnit 与失败取证 |
| Pillow | 12.2.0 | PyPI 官方包（已存在） | Python site-packages | 图片读取、裁剪、中文标注 | 通过：尺寸读取、裁剪、标注 |
| OpenCV | 5.0.0.93 | PyPI 官方包（已存在） | Python site-packages | 差异、阈值、形态学、连通区域 | 通过：差异区域定位 |
| numpy | 2.4.4 | PyPI 官方包（已存在） | Python site-packages | 图像矩阵计算 | 通过：差异指标 |
| OpenCode CLI | 1.19.3 | npm `opencode-ai`（官方） | `npx` 缓存，未全局安装 | 配置/Skill/Command/命令验证 | 通过：debug config/skill、mcp list、run --command |
| Playwright MCP 服务端 | 1.64.0-alpha | `@playwright/mcp` 依赖 | `node_modules` | MCP 浏览器实现 | 通过：25 工具列表与截图 |

说明：

- 没有执行管理员权限安装，没有修改系统级配置，没有删除既有项目内容。
- Playwright MCP 当前 `enabled: true`，用于完整命令链演练。25 个工具会常驻上下文；不需要时可把 `opencode.json` 中 `enabled` 改回 `false`。CLI 仍保留为手动/脚本通道。
- Playwright MCP 使用已安装的 Chrome channel，没有额外下载整套浏览器。

## 3. Skills 与 Commands 清单

### 3.1 项目级 Skills

全部位于 `.opencode/skills/<name>/SKILL.md`，已用 `opencode debug skill` 实际发现（6/6，缺失 0）。

| Skill | 职责 | 验证 |
|---|---|---|
| `mooctest-web-testing` | 总调度、阶段推进、状态/证据门禁、交付检查 | 已加载；`/web-test --check` 输出 `WEB_TEST_READY` |
| `test-case-design` | 需求分析、等价类、边界值、判定表、状态迁移、异常输入、审查去重 | 已加载；`/generate-test-cases --check` 输出 `TEST_CASE_READY`；生成 12 条主用例 + 1 条受控失败用例 |
| `browser-exploration` | 快照、DOM/定位、交互路径、控制台/网络、探索证据 | 已加载；浏览器验收用例 `TC-BROWSER-001` 通过 |
| `selenium-testing` | Page Object、显式等待、断言、隔离、失败取证 | 已加载；`/run-selenium --check` 输出 `SELENIUM_READY`；8 条 pytest 执行 |
| `visual-testing` | 截图、差异、区域、裁剪、标注、证据归档 | 已加载；`/visual-check --check` 输出 `VISUAL_CHECK_READY`；差异/裁剪/标注实测 |
| `test-reporting` | 汇总 JUnit/manifest/证据、生成 Markdown/HTML、缺陷清单 | 已加载；`/generate-test-report` 完成真实报告生成并校验 |

复用/评估已有 Skills：

| Skill | 来源与许可证 | 本次处理 |
|---|---|---|
| `playwright-cli` | Microsoft `@playwright/cli` 0.1.22，Apache-2.0（本地 package.json 验证） | 保留，浏览器主通道 |
| `test-case-writing` | `naodeng/awesome-qa-skills`（按 `SKILLS_INSTALL_REPORT.md` 安装）；远程许可证复核超时 | 保留，写作模板 |
| `test-case-reviewer` | 同上 | 保留，评审模板 |
| `ui-test-selenium` | 同上 | 保留，自动化模板 |
| `breakdown-test` | `github/awesome-copilot`（单文件）；远程许可证复核失败 | 保留但不作为核心依赖 |
| `boundary-value-testing` / `equivalence-partitioning` | 未单独安装 | 等价类/边界能力内建到 `test-case-design` |
| `webapp-testing` / `playwright-generate-test` | 未单独安装 | 探索与测试生成由 `browser-exploration`/`selenium-testing` 覆盖 |
| `skill-creator` | 未安装 | 按 OpenCode Skill 规范手工编写 |

说明：Playwright 两个包已从本地 `package.json` 确认 Apache-2.0；对已有 QA Skills 的远程 LICENSE 请求本次超时，未完成许可证复核。为避免为凑名称引入不兼容或低质量依赖，缺失能力采用项目级等效实现，这是主动取舍。

### 3.2 项目级 Commands

全部位于 `.opencode/commands/*.md`。5 个命令均在新的 OpenCode CLI 会话中实际加载并调用工具；`/generate-test-report` 额外完成真实报告生成。

| Command | 作用 | 实测结果 |
|---|---|---|
| `/visual-check` | 视觉检查、截图、差异、裁剪、标注、证据登记 | `--check` 加载 `visual-testing`，检查 Python/Pillow/OpenCV/脚本，输出 `VISUAL_CHECK_READY` |
| `/web-test` | 需求→用例→探索→Selenium→截图→报告闭环 | `--check` 加载 `mooctest-web-testing`，检查依赖/Skill/证据，输出 `WEB_TEST_READY` |
| `/generate-test-cases` | 生成等价类/边界/异常/业务流程用例并审查 | `--check` 加载 `test-case-design`，输出 `TEST_CASE_READY` |
| `/run-selenium` | 执行 Selenium/pytest，汇总断言与失败证据 | `--check` 加载 `selenium-testing`，核对 Chrome/驱动/Selenium/pytest，输出 `SELENIUM_READY` |
| `/generate-test-report` | 生成 Markdown/HTML 报告与缺陷清单 | 完整执行：生成报告、运行证据校验，输出 `REPORT_READY`；`--check` 也可用 |

注意：Desktop 已打开的会话不会热加载新 Skills/Commands；重启后 TUI 才会出现 `/web-test` 等命令。CLI 新会话会立即读取。

## 4. 真实测试结果

### 4.1 运行总览

| 指标 | 实际值 |
|---|---|
| 运行 ID | `RUN-20261029-02` |
| 目标 | `https://demo.playwright.dev/todomvc` |
| pytest 用例 | 8（7 passed，1 xfailed，0 failed，0 errors） |
| pytest 耗时 | 10.62 s |
| manifest 用例 | 11（10 passed，1 xfailed） |
| 证据条目 | 33（33/33 SHA-256 校验通过，0 缺失，0 不一致） |
| 产品缺陷 | 0 |
| 报告 | `reports/executions/RUN-20261029-02/report.md` / `.html` |
| 缺陷清单 | `reports/defects/RUN-20261029-02-defects.md` |

### 4.2 测试 1：浏览器能力

- 工具：Microsoft Playwright CLI 0.1.22，Chrome 155。
- 实际步骤：
  1. 打开 `https://demo.playwright.dev/todomvc`，标题 `React • TodoMVC`。
  2. 获取无障碍快照，定位输入框 `textbox "What needs to be done?" [ref=e8]`。
  3. 输入 `Acceptance todo` 并回车。
  4. 再次快照，列表出现 `listitem` 文本 `Acceptance todo`，计数 `1 item left`。
- 证据：
  - `evidence/raw/RUN-20261029-01/exploration/snapshot.yml`
  - `evidence/raw/RUN-20261029-01/exploration/after-add.yml`
- 结果：通过。

Playwright MCP 独立验证：

- 直接启动 MCP 服务端，协议 `2025-06-18`，工具列表 25 个。
- 调用 `browser_navigate`、`browser_snapshot`、`browser_take_screenshot` 全部成功。
- 证据：`evidence/raw/RUN-20261029-01/mcp/mcp-smoke.json`、`mcp-snapshot.yml`、`mcp-screenshot.png`。
- 结论：MCP 功能可用；当前 `enabled: true`，用于完整命令链探索，可关闭以控制上下文。

### 4.3 测试 2：截图能力

| 类型 | 文件 | 尺寸 | 校验 |
|---|---|---|---|
| 视口 | `evidence/raw/RUN-20261029-01/browser/viewport.png` | 1280×720 | Pillow 可读，非空 |
| 整页 | `evidence/raw/RUN-20261029-01/browser/fullpage.png` | 1280×720 | Pillow 可读，非空 |
| 元素（待办项） | `evidence/raw/RUN-20261029-01/browser/element-todo-item.png` | 550×59 | Pillow 可读，非空 |
| 元素（状态栏） | `evidence/raw/RUN-20261029-01/browser/element-footer.png` | 550×42 | Pillow 可读，非空 |
| MCP 截图 | `evidence/raw/RUN-20261029-01/mcp/mcp-screenshot.png` | 1280×720 | Pillow 可读，非空 |

Selenium 失败取证另外生成：

- `TC-TODO-099__failure__viewport__*.png`
- `TC-TODO-099__failure__fullpage__*.png`
- `TC-TODO-099__failure__page-source__*.html`
- `TC-TODO-099__browser__*.log`
- 用例日志：`evidence/logs/RUN-20261029-02/TC-TODO-099.log`

### 4.4 测试 3：Selenium 能力

命令：

```powershell
python tools\run_selenium.py --run-id RUN-20261029-02 --target https://demo.playwright.dev/todomvc --capture-pass
```

结果：

```text
7 passed, 1 xfailed in 9.59s
JUnit: tests=8 failures=0 errors=0 xfailed=1
```

- 成功用例：TC-TODO-001 ~ TC-TODO-007（新增、完成/过滤、编辑、删除、空/空白、长度边界、HTML 转义）。
- 受控预期失败：TC-TODO-099。故意断言“2 items left”，实际“1 item left”，pytest `xfail(strict=True)` 捕获；失败截图/整页截图/页面源码/浏览器日志/用例日志均已保存。
- 该 xfailed 不是产品缺陷，不计入通过率。
- 产物：
  - `reports/executions/RUN-20261029-02/junit.xml`
  - `reports/executions/RUN-20261029-02/junit-summary.json`
  - `evidence/logs/RUN-20261029-02/pytest-console.log`
  - `evidence/logs/RUN-20261029-02/pytest.log`
  - 各用例日志 `TC-TODO-*.log`

### 4.5 测试 4：图像处理

对同一视口的新增前/后截图执行：

```powershell
python tools\visual_diff.py compare `
  evidence/raw/RUN-20261029-01/browser/viewport.png `
  evidence/raw/RUN-20261029-01/browser/fullpage.png `
  --out-dir evidence/diff/RUN-20261029-02/TC-TODO-001-before-after `
  --label "TodoMVC 添加待办前后" --threshold 25 --min-area 30
```

实测指标：

| 指标 | 值 |
|---|---|
| 图像尺寸 | 1280×720 / 1280×720 |
| 原始变化像素 | 13,433 |
| 形态学后变化像素 | 8,122 |
| 差异比例 | 0.8813% |
| 平均绝对差 | 1.7283 |
| RMSE / PSNR | 7.8533 / 30.2297 dB |
| 差异区域 | 5 个；最大 550×15，面积 7564 |
| 判定 | `visual-change-detected`（受控变化，待人工复核） |
| 缺陷声明 | `false` |

产物：

- `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/annotated.png`
- `comparison.png`、`heatmap.png`、`diff.png`、`mask.png`
- `metrics.json`、`regions.json`
- 裁剪：`evidence/annotated/RUN-20261029-02/TC-TODO-001/new-item-crop.png`（550×48）
- 中文标注：`evidence/annotated/RUN-20261029-02/TC-TODO-001/new-item-annotated.png`

原始截图未修改；派生图单独存放。

### 4.6 测试 5：测试报告

命令：

```powershell
python tools\generate_report.py --run-id RUN-20261029-02 --title "Web 应用测试执行报告"
```

产物：

- `reports/executions/RUN-20261029-02/report.md`（含目标、环境、步骤、预期、实际、状态、截图路径、日志路径、缺陷说明、覆盖缺口）
- `report.html`（自包含样式，引用本地证据）
- `report.json`（结构化数据）
- `reports/defects/RUN-20261029-02-defects.md`（本轮 0 缺陷）

报告已区分：

- JUnit 支撑的 8 条 pytest 用例（7 passed + 1 xfailed）。
- 3 条非 JUnit 验收登记（TC-BROWSER-001、TC-VISUAL-001、TC-VISION-001）。
- 未执行：TC-TODO-008/009/010/012；部分覆盖：TC-TODO-011。

### 4.7 测试 6：Skills、Commands 与模型视觉

- `opencode debug skill`：实际发现 6 个新 Skill，缺失 0。
- 5 个 Command 均在新会话中加载并调用工具，输出对应 READY。
- `/generate-test-report` 完整执行并生成报告。
- 模型视觉实测：

```powershell
npx -y opencode-ai@1.19.3 run --auto `
  --file "evidence/raw/RUN-20261029-01/browser/element-todo-item.png" `
  -- "只回答：图片中是否包含文本 Acceptance todo？..."
```

模型回答：

```text
有。图片中显示一个圆形复选框元素，右侧为蓝色文本“Acceptance todo”。
```

结论：当前模型可接收图像并完成基础视觉识别；日志 `evidence/logs/RUN-20261029-02/vision-check-utf8.log`（UTF-16）。

### 4.8 证据校验

```powershell
python tools\evidence.py verify --run-id RUN-20261029-02 --fail-on-error
```

```json
{"checked": 33, "ok": 33, "missing": [], "mismatched": []}
```

索引：`evidence/INDEX.md`。

## 5. 失败与遗留问题

### 5.1 已修复的失败

1. **首次 pytest 运行 `RUN-20261029-01` 内部错误**
   - 现象：`AttributeError: 'TestReport' object has no attribute 'config'`，pytest exit=3。
   - 原因：在 `pytest_runtest_logreport` 中访问了不存在的 `report.config`。
   - 修复：把结果统计移到 `pytest_runtest_makereport(item, call)`，通过 `item.config` 获取运行配置；重新执行 `RUN-20261029-02`，7 passed + 1 xfailed。
   - 处理：失败的 `RUN-20261029-01` 保留在 manifest 中，未删除、未伪装为成功。

2. **`playwright-cli open` 进程未在 120s 内返回**
   - 现象：工具调用超时并杀掉子进程，但浏览器会话已建立。
   - 验证：`playwright-cli list` 显示 `bootstrap` 会话 open；后续 `snapshot`、`fill`、`screenshot` 全部成功。
   - 处理：不重复 open；用短超时 + `list` 校验；后续命令均正常。

3. **PowerShell 5.1 控制台中文乱码**
   - 现象：`Get-Content`/`Tee-Object` 显示 `?` 或乱码。
   - 验证：文件本身为 UTF-8/UTF-16；用 Python 读取和 `read` 工具检查，报告/CSV 均无替换字符。
   - 处理：报告与 CSV 使用 UTF-8（CSV 带 BOM）；视觉日志为 UTF-16；最终以文件内容为准。
   - 影响：一次 `/generate-test-report` 会话误判 CSV 中文损坏并重建；事后用 Python 校验，CSV 为 13 行、UTF-8 BOM、无替换字符。最终以文件校验为准。

4. **`/web-test --check` 的一次摘要误报**
   - 现象：模型在 check 摘要中称 `run_id=RUN-20261029-02` 尚未创建；实际 manifest 中该运行已存在。
   - 处理：命令模板已加固，要求先执行 `python tools/evidence.py summary --run-id <run_id>`，不存在时输出 `RUN_NOT_FOUND`，禁止猜测；后续以 manifest/summary 为准。

5. **首次完整 `/web-test` 在浏览器探索阶段阻塞**
   - 现象：`RUN-CMDCHECK-01` 在 `playwright-cli open` 处卡住，未完成探索/Selenium/报告。
   - 处理：标记 `blocked`，保留已生成用例；启用 Playwright MCP，更新 `browser-exploration` 与 `web-test.md`，Agent 改用 `browser_navigate`。
   - 结果：`RUN-CMDCHECK-03` 完整通过。

6. **Command 模式判断误停**
   - 现象：`RUN-CMDCHECK-02` 把 `--check` 就绪检查当成完整任务，输出 `WEB_TEST_READY` 后停止，未创建运行。
   - 处理：把 `web-test.md` 改成明确的 A/B 模式分支：含 `--check` 只执行 A 节；不含则直接执行 B 节。

7. **报告生成器回归**
   - 现象：命令链修改 `tools/generate_report.py` 以按 run 选用例文件后，`RUN-20261029-02` 报告的中文标题和覆盖缺口丢失。
   - 处理：修复 `_case_rows`，优先匹配含 `executed_in_run` 的命令链 CSV，否则回退到原始 `todomvc-test-cases.csv`；三份报告重新生成并通过证据校验。

### 5.2 有意保留的取舍

1. **Playwright MCP 当前启用**
   - 已验证可用（25 工具、截图、快照）。
   - 完整命令链演练使用 MCP 作为 Agent 探索通道；25 个工具会占用上下文，不需要时可改回 `enabled: false`。
   - Desktop 新会话会显示 `browser_*` 工具；CLI 仍保留为手动/脚本通道。

2. **未新建自定义 Agent**
   - 使用 OpenCode 内置 `build` agent + 项目 Skills/Commands。
   - 理由：避免重复的系统提示与权限配置；现有工作流已能约束行为。

3. **未安装全部同名外部 Skills**
   - `boundary-value-testing`、`equivalence-partitioning`、`webapp-testing`、`playwright-generate-test`、`skill-creator` 未单独安装。
   - 等效能力内建到 `test-case-design`、`browser-exploration`、`selenium-testing`，避免为凑名称引入不可用依赖。

### 5.3 未覆盖场景与限制

- 仅验证了公开演示站 TodoMVC，**未在 2026 正式赛题/竞赛平台验证**。
- 功能用例未覆盖：TC-TODO-008 刷新持久化、TC-TODO-009 全部完成/取消全部、TC-TODO-010 清除已完成、TC-TODO-012 键盘可访问性；TC-TODO-011 仅部分覆盖。
- 浏览器仅验证 Chrome 155；Edge 已安装但未跑自动化，Firefox/WebKit 未验证。
- 视觉差异仅验证了受控的单页变化；动态地图瓦片、动画、字体渲染等场景需要额外 mask 和阈值调参。
- 模型视觉仅验证“识别截图中文本/控件”这一基础能力，未做复杂图表、遮挡、细小缺陷的视觉推理基准。
- 未做性能、并发、跨浏览器矩阵、真实登录/权限场景。
- 未对正式比赛系统做任何扫描、修改或未授权访问。
- 许可证复核：Playwright 组件 Apache-2.0 已从本地 `package.json` 确认；已有 QA Skills 的远程 LICENSE 请求超时，未完成复核，正式比赛前需自行确认。
- 比赛合规性未由官方确认；使用前必须检查当届赛项对 AI 辅助工具的要求。

## 6. 项目目录与使用方式

```text
<PROJECT_ROOT>\
├── opencode.json                    项目级 MCP 配置（playwright 默认 disabled）
├── AGENTS.md                        项目规则：证据优先、禁止编造、显式等待
├── .opencode/
│   ├── skills/                      6 个项目级 Skills
│   └── commands/                    5 个项目级 Commands
├── docs/
│   ├── WORKFLOW.md                  流水线、阶段门禁、效率/安全规则
│   ├── CONVENTIONS.md               目录、ID、证据、截图、报告约定
│   ├── DEPLOYMENT.md                重新部署与排障
│   └── ACCEPTANCE_REPORT.md         本报告
├── tools/
│   ├── evidence.py                  证据清单、哈希、索引、校验
│   ├── visual_diff.py               差异/裁剪/标注/检查
│   ├── run_selenium.py              pytest + JUnit + 证据
│   ├── generate_report.py           Markdown/HTML/JSON 报告
│   ├── mcp_smoke.js                 Playwright MCP 冒烟
│   ├── register_acceptance.py       验收证据登记
│   └── driver/chromedriver.exe      固定驱动 155
├── tests/
│   ├── conftest.py                  driver、失败截图、manifest、日志
│   ├── pages/todo_page.py           Page Object 示例
│   ├── test_todomvc.py              7 条功能用例
│   └── test_todomvc_expected_failure.py  受控 xfail
├── reports/
│   ├── test-cases/                  用例设计 Markdown + CSV
│   ├── executions/RUN-20261029-02/  JUnit + report.md/html/json
│   └── defects/                     缺陷清单
├── evidence/
│   ├── raw/                         原始截图/快照/页面源码
│   ├── annotated/                   裁剪/中文标注
│   ├── diff/                        差异图/热力图/指标/区域
│   ├── logs/                        运行/控制台/用例/浏览器日志
│   ├── manifest.json                唯一证据索引
│   └── INDEX.md                     人类可读索引
└── backups/                         依赖文件备份
```

### 6.1 以后如何调用

1. **重启 OpenCode Desktop**，让新 Skills/Commands/MCP 配置生效。
2. 在 TUI 输入 `/web-test target=<URL> requirement=<需求文件> run_id=<RUN>`。
3. 或分阶段调用：
   - `/generate-test-cases requirement=... module=...`
   - `/visual-check target=... case_id=...`
   - `/run-selenium run_id=... target=...`
   - `/generate-test-report run_id=...`
4. 直接脚本：
   - `python tools\run_selenium.py ...`
   - `python tools\visual_diff.py ...`
   - `python tools\generate_report.py ...`
   - `python tools\evidence.py verify --fail-on-error`
5. MCP 当前已启用；如需关闭，把 `opencode.json` 的 `playwright.enabled` 改为 `false` 并重启 Desktop。用 `npx -y opencode-ai@1.19.3 mcp list` 确认连接状态。
6. 交付前运行证据校验，确保 0 缺失、0 哈希不一致。

## 7. 下一步建议

1. **用往届真实赛题做一次限时演练**：优先 2025 Web 应用测试预选赛“百度地图”类题目，按“需求→用例→探索→Selenium→截图→报告”全流程跑一遍，记录耗时与卡点。
2. **建立赛题专用 Page Object 库**：地图搜索框、路线规划、缩放控件、标记点、结果列表等；选择器集中管理，避免每次重写。
3. **处理动态内容**：地图瓦片、广告、时间、动画用固定视口 + `--ignore-box` + 阈值调参；像素差异只作为复核信号。
4. **补齐未覆盖场景**：持久化、toggle-all、clear-completed、键盘可访问性；把用例 ID 与 pytest marker 一一对应。
5. **跨浏览器矩阵**：至少 Chrome + Edge；固定驱动/浏览器版本；记录每个组合的结果。
6. **数据驱动**：把等价类/边界值/异常输入做成参数化用例；用 CSV/JSON 管理测试数据。
7. **证据自动化**：失败即截图/源码/日志；报告自动关联；提交前跑 `verify --fail-on-error`。
8. **合规检查**：赛前确认当届赛项对 AI 工具、自动截图、外部库的限制；不把未授权工具带入正式比赛。
9. **可复现性**：保留 `docs/DEPLOYMENT.md`、依赖版本、驱动版本、备份；赛前不要升级全局环境。
10. **可选增强**：若赛题需要并行执行，再评估 `pytest-xdist`；当前不引入，避免并发下证据/驱动冲突。

## 8. 补充工具调用自检（RUN-TOOLCHECK-01）

在正式验收之后又做了一轮独立工具自检，运行 ID `RUN-TOOLCHECK-01`，6 个用例、36 条证据，36/36 SHA-256 校验通过，0 产品缺陷。

| 工具组 | 实际调用 | 结果 |
|---|---|---|
| Playwright CLI | open、snapshot、find、fill、click、hover、eval、resize、视口/整页/元素截图、console、requests、state-save、localStorage、tab-new/select/close、close | 全部成功 |
| Playwright MCP | navigate、type、wait_for、find、snapshot、click、evaluate、resize、console、network、tabs、screenshot、close（25 工具） | 14 个步骤全部成功 |
| Selenium | `test_add_todo`，显式等待、断言、通过截图、JUnit | 1 passed |
| 图像工具 | inspect、相同图 compare（0 像素/no-change）、前后图 compare（7981 像素/6 区域）、crop、annotate | 全部成功 |
| 证据 CLI | start-run、update-case、add-defect（临时虚拟缺陷）、summary、register、verify、index | 全部成功；临时运行已删除 |
| OpenCode 当前会话 | skill、task 子代理、glob、grep、webfetch、read image、bash、write、edit、todowrite | 全部成功 |

产物：

- `reports/executions/RUN-TOOLCHECK-01/report.md`
- `reports/executions/RUN-TOOLCHECK-01/report.html`
- `reports/executions/RUN-TOOLCHECK-01/report.json`
- 证据：`evidence/raw|diff|annotated|logs/RUN-TOOLCHECK-01/`

观察到但不构成产品缺陷：

- Playwright MCP 控制台记录 1 个资源加载错误（`browser_console_messages`），本轮未做业务断言，仅记录。
- `glob` 从项目根目录直接匹配 `.opencode/commands/*.md` 未命中（隐藏目录遍历行为）；用 `path=.opencode/commands` + `**/*.md` 可正常命中 5 个命令文件。

## 9. 完整 Command 级演练（RUN-CMDCHECK-03）

执行命令：

```text
/web-test target=https://demo.playwright.dev/todomvc run_id=RUN-CMDCHECK-03 scope=smoke module=TodoMVC-CMDCHECK3
```

实际链路：

- 加载 `mooctest-web-testing`、`test-case-design`、`browser-exploration`、`selenium-testing`、`visual-testing`、`test-reporting`。
- 新建运行 `RUN-CMDCHECK-03`，生成 9 条 TodoMVC 用例（`reports/test-cases/TodoMVC-CMDCHECK3-test-cases.md` / `.csv`）。
- 探索使用 Playwright MCP：`browser_navigate`、`browser_snapshot`、`browser_type`、`browser_take_screenshot`；验证 `input.new-todo`、`.todo-list li`、`span.todo-count`、`footer.footer`。
- Selenium smoke：`test_add_todo` 通过（1 passed，3 条断言）。
- 截图：元素 550×59、视口 1280×720、整页 1262×748；Pillow 校验非空。
- 报告：`reports/executions/RUN-CMDCHECK-03/report.md` / `.html` / `.json`；证据 7/7 校验通过。
- 未覆盖：TC-TODO-002~009（smoke scope），报告已如实列出。

过程中的失败与修复：

- `RUN-CMDCHECK-01` 在 `playwright-cli open` 阶段阻塞，标记为 `blocked`；保留已生成的用例文件，不伪装完成。
- `RUN-CMDCHECK-02` 因 Command 模式判断误停在 `--check` 就绪检查，未创建运行；已把 `web-test.md` 改成明确的 A/B 模式分支。
- `RUN-CMDCHECK-03` 通过；MCP 成为 Agent 探索主通道。
- 命令链曾修改 `tools/generate_report.py` 以按 run 选用例文件；回归时发现原验收报告的中文标题和覆盖缺口丢失，已修复 `_case_rows` 兼容“命令链 CSV”和“原始验收 CSV”，并重新生成、校验 `RUN-20261029-02`、`RUN-TOOLCHECK-01`、`RUN-CMDCHECK-03` 三份报告。

## 10. 验收结论

- 浏览器探索、DOM/无障碍快照、交互、视口/整页/元素截图：**真实验证通过**。
- Selenium + pytest + 显式等待 + 断言 + 失败取证 + JUnit：**真实验证通过**。
- Pillow/OpenCV 图像读取、差异、区域定位、裁剪、中文标注：**真实验证通过**。
- 证据 manifest、SHA-256 校验、Markdown/HTML 报告：**真实验证通过**（`RUN-20261029-02` 33/33、`RUN-TOOLCHECK-01` 36/36、`RUN-CMDCHECK-03` 7/7）。
- 6 个项目级 Skills、5 个 Commands：**实际加载/调用通过**；`/generate-test-report` 完成真实任务。
- 完整 `/web-test` 命令链：新建运行 → 用例 → MCP 探索 → Selenium → 截图 → 报告：**真实验证通过**（`RUN-CMDCHECK-03`，1 passed，7/7 证据）。
- 模型图像输入：**实测通过**（基础识别）。
- 未完成/未验证：正式赛题、跨浏览器矩阵、全部边界/可访问性场景、复杂动态视觉场景。上述限制已在本报告第 5 节明确列出，未标记为成功。
