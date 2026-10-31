---
name: selenium-testing
description: 设计并执行 Selenium + pytest Web 自动化：Page Object、稳定定位、显式等待、业务断言、用例隔离、失败截图/页面源码/浏览器日志和 JUnit 结果。适用于 /run-selenium、自动化脚本生成与调试。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: selenium
---

# selenium-testing

先读 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。浏览器探索已完成时，直接复用其中的稳定选择器和交互路径。

## 本机环境

版本值不要抄写，实时值用 `python tools/env_check.py` 读取（返回 `verdict` 与各项 detail）。

- Python 3.13.9，Selenium 4.51.0，pytest 9.1.1（2026-10-31 实测）。
- Chrome 与 ChromeDriver 必须主版本一致；不一致时 `env_check` 返回 `BLOCKED`，`tests/conftest.py` 也会在建立会话前直接失败。
- 固定驱动：`tools/driver/chromedriver.exe`；来源、哈希与升级步骤见 `tools/driver/DRIVER.md`。
- 页面对象示例：`tests/pages/todo_page.py`（仅 TodoMVC 回归基线，新站点不得复用它）。
- 新站点生成的 Page Object 与测试放在 `tests/generated/<slug>/`。
- 失败取证与 manifest 集成：`tests/conftest.py`。

## 执行

```powershell
python tools/run_selenium.py --run-id <RUN_ID> --target <URL> --capture-pass
python tools/run_selenium.py --run-id <RUN_ID> --suite tests/test_todomvc.py --marker acceptance
python -m pytest -q -k "add_todo"   # 调试单条，仍需带 --run-id
```

产物：

- `reports/executions/<run>/junit.xml`
- `reports/executions/<run>/junit-summary.json`
- `evidence/logs/<run>/pytest.log`
- `evidence/logs/<run>/pytest-console.log`
- `evidence/logs/<run>/<case_id>.log`
- 失败：视口/整页截图、页面源码、浏览器日志。

## 设计规则

1. **Page Object**：选择器集中；页面方法只做动作，断言留在测试。
2. **显式等待**：`WebDriverWait` + `expected_conditions` 或业务 lambda；禁止用固定 `time.sleep`。
3. **断言可观察**：文本、URL、数量、可见性、属性、localStorage 状态；不要只断言“元素存在”。
4. **隔离**：每个用例清理 localStorage/会话；失败不污染下一条。
5. **稳定定位**：`id`、`data-testid`、稳定 class、role+name；避免绝对 XPath 和依赖 DOM 顺序。
6. **有限重试**：只对明确的瞬时问题重试 1 次；重复提交类动作不要盲目重放。
7. **资源释放**：`driver.quit()` 放在 finally；会话级 driver 只在套件结束时关闭。
8. **失败传播**：不要 `except: pass`；让 pytest 记录失败并触发取证。

## 测试模板

```python
import pytest
from pages.todo_page import TodoPage

@pytest.mark.case_id("TC-XXX-001")
def test_example(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("打开页面并执行动作")
    page.open()
    case_ctx.check(page.item_texts() == ["预期"], "业务断言", ["预期"], page.item_texts())
    case_ctx.screenshot("关键状态", full_page=True)
```

- `case_ctx.check` 会写入断言明细；失败会抛出 AssertionError。
- `case_ctx.screenshot` 会把截图登记到 manifest。
- 受控失败用 `@pytest.mark.xfail(strict=True)`，并在报告中单列，不计入通过率。

## 常见问题

| 现象 | 优先检查 |
|---|---|
| 启动失败/版本不匹配 | Chrome 与 chromedriver 主版本；`tools/driver` 是否存在 |
| 元素不可点击 | 是否被遮挡、是否在视口外、是否需要滚动/等待可点击 |
| StaleElementReference | 页面重渲染；重新查找元素并等待新状态 |
| 删除/编辑按钮点不到 | 按钮 hover 才显示；用 ActionChains 先悬停 |
| 无头模式布局不同 | 固定 window-size、device-scale-factor；必要时用 headed 复核 |
| 用例相互影响 | localStorage/session 未清理；是否复用同一 driver |
| 失败没有截图 | 是否通过 `run_selenium.py`/pytest 运行；driver 是否在 funcargs 中 |

## 输出

- `tests/` 下的 Page Object 与测试。
- JUnit、控制台日志、失败证据。
- 运行摘要和已知缺口，交给 `test-reporting`。
