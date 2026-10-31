---
description: 生成 Markdown/HTML 测试报告、缺陷清单并校验证据
agent: build
---

目标：$ARGUMENTS

先加载 `test-reporting` Skill，并读取 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。

## 参数约定

- `run_id=<RUN-...>`：必填（或从最近运行推断）。
- `title=<text>`：报告标题。
- `--check`：只检查 manifest、JUnit、证据完整性，不生成报告。

## 步骤

1. `--check`：
   - `python tools/evidence.py summary --run-id <run_id>`
   - `python tools/evidence.py verify --run-id <run_id> --fail-on-error`
   - 检查 `reports/executions/<run>/junit-summary.json` 是否存在。
   - 输出 `REPORT_READY` 或明确缺失项，停止。
2. 生成：`python tools/generate_report.py --run-id <run_id> --title "<title>"`。
3. 校验：`python tools/evidence.py verify --run-id <run_id> --fail-on-error`。
4. 检查报告：
   - 通过数与 JUnit 一致；`xfailed` 单列；
   - 每个失败用例有截图/源码/日志链接；
   - 没有证据的用例标注“证据不完整”；
   - 视觉差异只写“受控变化/待复核”，不写未证实缺陷。
5. 输出：`report.md`、`report.html`、`report.json`、`reports/defects/<run>-defects.md` 的路径；证据校验结果；未覆盖场景。
