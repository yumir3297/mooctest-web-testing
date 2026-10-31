# Selenium Agent 执行规则（AI 可执行版）— 部分过时

> ## ⚠ 状态：PARTIAL（2026-10-31 复核；有效条款保留，版本信息过时）
>
> - **仍有效**：§3 定位优先级、§4 显式等待（禁止 sleep 兜底）、§5 断言、§6 异常与重试、§7 失败分类码、§10 行为约束。
> - **已过时**：§1 环境与版本硬约束中的具体版本号（Chrome 155 / Driver 155 / Selenium 4.51.0 / Python 3.13.9 / pytest 9.1.1）是写入时快照，**不得**作为当前环境的判断依据；实时值一律以 `python tools/env_check.py` 的输出为准。
> - **命名冲突**：§8、§9 的 `SHOT-{TC_ID}-...`、`test_TC-WEB-...` 命名已废止，改用 `docs/CONVENTIONS.md`（`<case_id>__<stage>__<kind>__<UTC>.<ext>`、`TC-<模块>-<三位序号>`）。
> - **规范来源**：工作流与工具选择见 `docs/WORKFLOW.md`，Selenium 编码规范见 `.opencode/skills/selenium-testing/`。
>
> 以下正文保留原样；与上述冲突处以本节为准。

> 目标：让 Agent 在「探索 → 编码 → 执行 → 纠错 → 取证」每一步都有明确的判定规则，而不是靠试错。
> 来源标注 `[S-xx]` 见文末；版本类规则以官方现行文档为准。
> 分工：**浏览器探索**用 playwright-cli；**最终交付代码**必须用 Selenium（比赛指定）。

---

## 1. 环境与版本硬约束

| 项 | 要求 | 依据 |
|---|---|---|
| Selenium | ≥ 4.0（本地实测 4.51.0） | `[S-11]` 2025 赛项说明；`[S-13]` Python API |
| Python | ≥ 3.8（本机 3.13.9） | `[S-11]` |
| pytest | ≥ 7.0（本机 9.1.1） | `[S-11]`、`[S-14]` |
| 浏览器 | Chrome ≥ 130（本机 155） | `[S-11]` |
| 驱动 | 与浏览器版本匹配，**固定版本**，显式传 `Service(executable_path=...)` | 本机实测：Selenium Manager 自动下载会挂起 |
| 并发 | 每个 session 独立账号，不共享登录态 | `[S-12]` 测试独立性 |

规则：版本冲突时先核对上表，再改代码；不允许「降级绕过」。

---

## 2. 探索阶段（playwright-cli）规则

1. 探索只做三件事：**确认元素稳定可定位**、**确认交互路径可走通**、**确认等待条件可观测**。
2. 每次探索必须留下证据：`snapshot`（结构）+ 截图 + 关键元素的 `data-testid/id/name`。
3. 探索出的路径必须能翻译成 Selenium 动作序列；翻译不了的（依赖浏览器专有 API）直接判为不可自动化。
4. 探索不得把 playwright 代码带入最终交付物。

---

## 3. 元素定位规则（优先级从高到低）

1. `id`
2. `data-testid` / `data-*` 业务标记
3. `name`
4. 关联 `label`、`aria-label`、可见文案（`linkText` / `xpath` 文本谓词）
5. 稳定 CSS：`[placeholder='xxx']`、`form >> input[type=...]`（相对定位器）
6. 最后才是 XPath 结构定位

**禁止**
- 绝对 XPath（`/html/body/div[3]/...`）
- 依赖位置索引（`div:nth-child(4)`）
- 依赖样式类名（`el-button--primary` 这类会随构建变化的类）
- 依赖动态生成的随机 id

**校验要求**：每个定位器至少满足两条——唯一命中（`find_elements` 数量 == 1）、在页面结构变化（弹窗开关/列表滚动）后仍成立。

依据：`[S-12]` 元素定位与可维护性；`[S-06]` AI Agent 使用 Selenium 的官方建议。

---

## 4. 等待规则（禁止 sleep 兜底）

| 场景 | 必用条件 |
|---|---|
| 元素存在 | `presence_of_element_located` |
| 元素可见 | `visibility_of_element_located` |
| 元素可点击（未禁用/未被遮挡） | `element_to_be_clickable` |
| 文案/数值变化 | `text_to_be_present_in_element` |
| 元素消失（加载遮罩） | `invisibility_of_element_located` |
| 列表数量变化 | 自定义 `expected_conditions`（`len(...) == n`） |
| 页面跳转完成 | `url_contains` / `url_to_be` + 目标元素可见（双条件） |

**规则**
1. 统一 `WebDriverWait(driver, timeout).until(...)`，超时值集中配置（默认 10s，慢页面 20s）。
2. 严格不同时使用隐式等待与显式等待（官方明确禁止混用）`[S-08]`。
3. `sleep` 仅允许出现在「演示/截图对齐」场景，且必须注释原因；不得用于等待业务结果。
4. 等待失败必须抛 `TimeoutException` 并进入失败取证流程，不允许静默继续。

依据：`[S-08]` Selenium 官方 Waits 文档（含「Do not mix implicit and explicit waits」）。

---

## 5. 断言规则

1. **断言业务可判定结果**，不断言实现细节（不断言 class 名、不断言 DOM 层级）。
2. 每个用例至少 1 条「结果断言」+ 1 条「副作用断言」（数据/列表/URL/提示语任一）。
3. 断言消息必须包含：用例 ID、期望值、实际值、当前 URL。
4. 涉及金额/数量/时间：断言前统一格式化（去除千分位、货币符号、空白），避免格式差异导致假失败。
5. 失败不可吞异常：`assert` 或 `pytest.fail`，禁止 `try/except: pass`。

依据：`[S-09]` pytest 断言与实践；`[S-01]` 2025 评分对可复现性的要求。

---

## 6. 异常处理与重试

| 异常 | 判定 | 处理 |
|---|---|---|
| `NoSuchElementException` | 定位器失效 或 页面未渲染 | 先等条件再判定；超时后归类 LOCATOR 或 TIMING |
| `StaleElementReferenceException` | 页面重绘 | 用稳定定位器**重新查找**再操作；最多重试 2 次 |
| `ElementClickInterceptedException` | 被遮挡/动画未结束 | 等可点击条件；仍失败则滚动到可视区后再点，禁止 JS 点击兜底（除明确说明） |
| `TimeoutException` | 等待条件未满足 | 立即取证（截图+page_source+URL），归类 TIMING |
| `InvalidSessionIdException` / 浏览器崩溃 | 环境问题 | 终止该 session，归类 ENV，重跑一次 |
| `UnexpectedAlertPresentException` | 弹窗未处理 | 先处理弹窗再继续，归类 SCRIPT |

**禁止**：对资金/提交/删除类操作做「盲目重放」。这类操作的重试必须先确认服务端状态。

依据：`[S-08]`、`[S-09]`；行业实践（不稳定测试治理）。

---

## 7. 失败分类编码（统一用于日志与报告）

| 码 | 含义 | 责任方 | 典型信号 |
|---|---|---|---|
| `ENV` | 环境/网络/驱动 | 环境 | 驱动启动失败、证书错误、超时无响应 |
| `LOCATOR` | 元素找不到/定位器过期 | 脚本 | `NoSuchElement`、命中多个 |
| `TIMING` | 等待条件不成立 | 脚本或应用 | `TimeoutException`、条件始终 false |
| `DATA` | 测试数据不满足前置 | 数据 | 账号无效、数据被占用 |
| `SCRIPT` | 脚本逻辑错误 | 脚本 | 变量错误、断言语义错 |
| `APP` | 应用缺陷 | 产品 | 业务结果确实与需求不符 |
| `ASSERT` | 断言与预期不一致但原因未定 | 待查 | 需人工复核 |

规则：**`APP` 与 `ASSERT` 必须附截图 + 步骤复现路径**，否则视为无效结论。

---

## 8. 日志与取证规则

每次执行必须产出（按 `RUN-xxx` 聚合）：

1. **运行头**：浏览器版本、驱动版本、Selenium 版本、Python 版本、起始时间、用例集版本。
2. **用例级日志**：用例 ID、开始/结束时间、耗时、最终状态（PASS/FAIL/SKIP）、失败码。
3. **失败取证三件套**：整页截图 + `page_source` HTML + 当前 URL 与可见文案摘要。
4. **截图命名**：`SHOT-{TC_ID}-{序号}-{状态}.png`，与用例 ID 强绑定。
5. **退出保证**：`try/finally` 或 fixture 中必须 `driver.quit()`，避免僵尸进程。

依据：`[S-09]` 截图与调试实践；`[S-03]` 测试结果可追溯性。

---

## 9. 结构规则（便于评分与评审）

1. Page Object：一个页面/组件一个类，定位器为类常量，动作是方法，断言放测试层。
2. 用例与代码一一对应：`test_TC-WEB-001_xxx`，函数名含用例 ID。
3. 数据外置：`data/*.yaml|csv` 或 pytest `parametrize`，不硬编码在步骤里。
4. 独立性：任一用例可单跑，不依赖前一条用例产生的状态。
5. 可并行：默认不共享 driver，session 级 fixture 按需开启。

依据：`[S-12]` Page Object 与测试独立性；`[S-14]` pytest fixture/参数化。

---

## 10. Agent 自身的行为约束

- 不允许为了让用例「变绿」而放宽断言、删除断言或把失败改为 skip。
- 不允许在未取证的情况下声称「用例通过」。
- 每次修复定位器/等待后，必须重跑该用例并产出新证据。
- 探索结论（页面结构、元素稳定性）必须写回知识库或脚本注释，避免重复探索。

---

## 来源表

| 编号 | 资料 | 本地路径 |
|---|---|---|
| S-01 | 2025 Web 应用测试赛项说明（评分准则，历史基线） | `01_competition_official/P0-03_2025_web_track_spec.pdf` |
| S-03 | ISO/IEC/IEEE 29119-3 公开摘要（可追溯性，概念级） | `04_iso_public_summaries/` |
| S-06 | Selenium 官方：Using AI coding agents with Selenium | `03_selenium_pytest/P0-06_selenium_ai_agents_text.txt` |
| S-08 | Selenium 官方：Waits | `03_selenium_pytest/P0-08_selenium_waits_text.txt` |
| S-09 | Selenium 官方：Test Practices | `03_selenium_pytest/P0-09_selenium_test_practices_text.txt` |
| S-11 | 2025 赛项说明中的环境版本要求（Selenium ≥4.0 / Python ≥3.8 / pytest ≥7 / Chrome ≥130） | `01_competition_official/P0-03_2025_web_track_spec.pdf` |
| S-12 | Selenium 官方文档中的 Page Object 与测试独立性实践 | `03_selenium_pytest/P0-09_selenium_test_practices_text.txt` |
| S-13 | Selenium Python API 参考（核对现行 API 是否存在） | `03_selenium_pytest/P0-10_selenium_python_api_text.txt` |
| S-14 | pytest 官方 How-to（fixture / 参数化 / 断言） | `03_selenium_pytest/P0-11_pytest_howto_index_text.txt` |
