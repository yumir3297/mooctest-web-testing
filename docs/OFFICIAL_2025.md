# 2025 官方赛项规范与本项目适配

- 来源：`materials/赛题/2025-*/`（需求文档、功能说明手册、三类注意事项、`测试用例模版.xlsx`）
  与 `materials/参考答案/2025-*/`（参考实现 + screenshots）
- 性质：**2025 基线**。2026 官方规则未获取，本文与导出结果都不声称符合 2026 要求。
- 适配实现：`tools/export_official_2025.py`（导出 + 校验），并在 `tools/pre_submission_gate.py` 中作为 **G5** 接入。

## 1. 官方规范（三方交叉核实）

「注意事项 docx」「测试用例模版.xlsx」「参考答案」三处一致，可视为 2025 的稳定要求。

### 1.1 用例表（10 列，顺序固定）

| # | 列名 | 要求 |
|---|---|---|
| 1 | 测试用例编号 | `<被测软件名>_R<需求号3位>_<序号3位>`，如 `SF_R001_001`；**严格区分大小写**，需与需求文档的用例编号一致 |
| 2 | 模块名称 | 按需求文档给出的模块名，如「运费时效查询」 |
| 3 | 需求编号 | 按需求说明书，如 `R001` |
| 4 | 用例说明 | 该用例测什么 |
| 5 | 前置条件 | 登录态、数据初始状态 |
| 6 | 执行步骤 | 操作步骤，需与功能说明书描述一致 |
| 7 | 输入数据 | **一行一个输入**（Excel 内 Alt+Enter 换行） |
| 8 | 预期结果 | 从功能需求说明书中提取 |
| 9 | 实际结果 | 执行后的真实页面情况 |
| 10 | 截图文件名 | `<时间戳>_<测试用例编号>.png`，必须能对应到实际截图文件 |

### 1.2 测试代码

- 使用题目包提供的模板（`Test<App>.java` / `test_<App>.py`），代码只插入 `// test-code-start` 与 `// test-code-end` 之间。
- **一个需求一个测试函数**：`test_<App>_R<需求号>()`，如 `test_SF_R001`。需求文档有几条需求就只有几个函数，「不可多也不可少」。
- 不要在类名外添加注解；文件编码必须 UTF-8。
- 截图必须调用模板的 `takeScreenshot` / `take_screenshot`，**不得修改函数内容**。

### 1.3 测试截图

- 截图区域：整个浏览器窗口。
- 命名：`<时间戳>_<测试用例编号>.png`，时间戳由模板函数生成（`%H%M%S%d%f` 取前 11 位）。
- 全部放在 `screenshots/` 目录，**打包成 zip**（明确禁止 rar）。
- **一条用例只保留一张截图**，调试产生的多余截图必须删除。

## 2. 与本项目内部约定的差异

| 项 | 官方 2025 | 本项目内部 | 处理 |
|---|---|---|---|
| 用例编号 | `<App>_R001_001` | `TC-CART-001` | 导出时按 `requirement_ids` + 顺序生成官方编号；内部编号保持不变 |
| 用例表 | 10 列中文 | 16 列机器可读 | 导出生成本项目录的 `测试用例模版.xlsx`；内部 CSV 仍是唯一事实源 |
| 截图命名 | `<11位时间戳>_<编号>.png` | `<case>__<stage>__<kind>__<UTC>.png` | 导出时**复制**并重命名，原图不动（原始证据不可覆盖） |
| 截图目录 | `screenshots/` + zip | `submission/<RUN>/screenshots/` | 导出包内单独生成 |
| 代码结构 | 一需求一函数 | 一用例一函数（`tests/generated/<slug>/`） | 导出的 `Test<App>.py` 为官方骨架（每需求一个函数 + 截图调用点）；内部可运行实现放 `test-code/runner/` |
| 断言 | 参考实现 0 条断言，靠截图 + 人工复核 | 强制断言，无断言即 FAIL | 内部门禁更严；导出不因此放宽内部质量要求 |

**结论**：内部体系仍按「一用例一函数 + 断言」保证可复现性；官方格式由导出适配器生成。两者不互相污染。

## 3. 用法

```powershell
# 导出（读取内部 run + 用例表）
python tools/export_official_2025.py `
  --run-id RUN-20261031-COLDSTART-01 `
  --app CartCheck `
  --cases reports/test-cases/cartcheck-test-cases.csv `
  --module 结算试算 `
  --with-runner `
  --out official_2025

# 单独校验
python tools/export_official_2025.py --verify official_2025/RUN-20261031-COLDSTART-01 --json

# 作为质量门禁的 G5
python tools/pre_submission_gate.py --run-id <RUN> --cases <CSV> `
  --junit-summary <JSON> --submission submission/<RUN> `
  --official-2025 official_2025/<RUN> `
  --out qualification/gate-runs/<RUN>
```

产物：

```text
official_2025/<RUN>/
  测试用例模版.xlsx          10 列官方表
  screenshots/               <11位时间戳>_<官方编号>.png，一用例一张
  screenshots.zip            只含 screenshots/ 目录
  test-code/Test<App>.py     官方骨架：test-code-start/end + 每需求一个函数 + take_screenshot
  test-code/runner/          内部可运行实现（--with-runner）
  manifest.json              用例映射、截图来源、逐文件 sha256
  README.md                  2025 基线声明与缺口
```

## 4. 实际验证（2026-10-31）

用冷启动运行 `RUN-20261031-COLDSTART-01`（CartCheck）导出：

```text
profile=official-2025  app=CartCheck
case_count=30  requirement_count=10  screenshot_count=30  missing_screenshots=0
official_format_confirmed=2025-baseline-only
```

`--verify`：`ok=true / verdict=PASS / FAIL=0 / WARNING=1`，warning 为
`MULTI_REQUIREMENT_NARROWED`（24 条内部用例回指多个需求，导出时只保留第一个）。

门禁 G5：`G5=WARNING`，`delivery_verdict=WARNING`，`test_verdict=FAIL`，exit 0。

`test-code/runner/` 在项目外独立复跑：`5 failed, 25 passed`，与原始运行一致。

## 5. 已知限制

1. **多需求归属**：内部用例可以回指多个需求（例如同时验证「示例表」与「金卡折扣规则」），官方格式一行只能填一个需求编号。当前取第一个并给出 WARNING；如需精确归属，应在用例表中增加主需求字段。
2. **时间戳来源**：官方由 `take_screenshot` 在截图瞬间生成；导出时用证据登记时间 + 原文件名毫秒位还原，二者语义一致但不是同一次运行时生成。
3. **代码骨架不是成品**：`Test<App>.py` 只保证结构合规（函数与需求一一对应、标记齐全、`take_screenshot` 逐字一致），业务步骤需补全；可运行实现见 `test-code/runner/`。
4. **2026 未确认**：若 2026 更换模板或列定义，需以新模板为准重新适配。
5. **参考实现无断言**：这提示官方评分更依赖截图与人工复核；本项目仍保留断言，用于保证「测试有效」而不是「截图齐全」。
