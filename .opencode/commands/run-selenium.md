---
description: 执行 Selenium/pytest 用例，汇总断言、失败截图与 JUnit
agent: build
---

目标：$ARGUMENTS

先加载 `selenium-testing` Skill，并读取 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。

## 参数约定

- `target=<URL>`：目标站点；缺省用 `MOOCTEST_TARGET` 或 TodoMVC 演示页。
- `run_id=<RUN-...>`：证据运行 ID。
- `suite=<pytest path>`：缺省 `tests`。
- `marker=<expr>`、`keyword=<expr>`：可选筛选。
- `--capture-pass`：为通过用例也保存最终截图。
- `--headed`：有头模式排查布局问题。
- `--check`：只检查 Chrome/chromedriver/Selenium/pytest/驱动版本，不执行测试。

## 步骤

1. `--check`：读取 `tools/driver/chromedriver.exe --version` 与 Chrome 版本，确认主版本一致；导入 selenium/pytest；输出 `SELENIUM_READY` 或明确阻塞。
2. 运行：`python tools/run_selenium.py --run-id <run_id> --target <target> --capture-pass`（按需加 `--suite/--marker/--keyword`）。
3. 读取 `reports/executions/<run>/junit-summary.json` 与 `evidence/logs/<run>/pytest-console.log`。
4. 失败用例：检查视口/整页截图、页面源码、浏览器日志；分类为环境/定位/等待/业务失败。
5. 修复后只重跑受影响用例；在运行备注中记录重试原因。
6. 运行 `python tools/evidence.py verify --run-id <run_id> --fail-on-error`。
7. 输出：通过/失败/xfailed/阻塞数量、失败用例及证据路径；不要把 xfailed 计入通过率。
