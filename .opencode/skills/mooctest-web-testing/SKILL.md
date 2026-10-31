---
name: mooctest-web-testing
description: 总调度 Web 应用测试赛题：从需求分析、用例设计、用例审查、浏览器探索、Selenium 执行、视觉取证到测试报告，负责阶段推进、证据门禁和交付物验收。适用于 /web-test、完整测试闭环、比赛赛题演练。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: web-testing
---

# mooctest-web-testing

## 何时使用

- 用户要求对某个 Web 应用完成端到端测试，而不只是写几条用例。
- 需要把需求、用例、自动化、截图、缺陷和报告串成一条可追溯链路。
- 需要检查已有测试产物是否满足比赛交付要求。

先读 `docs/WORKFLOW.md` 和 `docs/CONVENTIONS.md`。如果任务只涉及单一阶段，直接加载对应专项 Skill，不要启动整套流程。

## 输入

至少确认：

- 目标 URL 或本地被测站点；
- 需求文档/验收标准/赛题说明（没有则明确假设）；
- 允许测试的范围与禁止操作；
- 交付格式（Markdown/HTML、用例表格式、截图要求）；
- 是否允许使用 AI 工具（比赛合规）。

## 编排顺序

1. `test-case-design`：需求分析、等价类、边界值、异常输入、业务流程用例、审查去重。
2. `browser-exploration`：真实页面结构、可访问性快照、稳定定位、交互路径。
3. `selenium-testing`：Page Object、显式等待、断言、失败取证。
4. `visual-testing`：必要截图、差异、裁剪、标注、证据归档。
5. `test-reporting`：汇总结果、证据、缺陷，生成 Markdown/HTML。

每个阶段结束更新运行状态：

```powershell
python tools/evidence.py update-run --run-id <RUN_ID> --stage <stage> --note "<实际结果>"
```

## 运行初始化

```powershell
python tools/evidence.py start-run --run-id <RUN_ID> --target <URL> --label "<赛题/模块>"
```

若用户未给 RUN_ID，使用 `RUN-YYYYMMDD-HHMMSS`。不要复用已完成的运行来掩盖失败；新执行建新运行。

## 阶段门禁

- 需求阶段：每个需求有来源、验收标准、风险级别。
- 用例阶段：正常/异常/边界至少各一条；每个输入域有等价类和边界；用例可执行、可观察、无重复。
- 探索阶段：定位器经过真实 DOM 验证；快照/截图已登记；不使用绝对 XPath。
- 自动化阶段：显式等待；断言绑定业务状态；用例隔离；失败有截图和日志。
- 视觉阶段：原始截图不可变；差异有指标和区域；不把像素差异直接写成缺陷。
- 报告阶段：`evidence.py verify --fail-on-error` 通过；报告不把未执行场景写成通过。

## 失败处理

1. 读取 `evidence/logs/<run>/`、失败截图、页面源码。
2. 分类：环境/驱动、定位、等待、测试数据、真实业务失败。
3. 环境问题修复环境；定位问题回浏览器探索；真实业务失败登记缺陷。
4. 只重跑受影响用例，记录重试原因。
5. 不能修复时明确写“阻塞”，不要伪装通过。

## 交付检查

- `evidence/manifest.json` 含运行、用例、证据、哈希。
- `reports/test-cases/` 有需求/用例/审查记录。
- `reports/executions/<run>/report.md` 与 `.html`。
- `reports/defects/<run>-defects.md`（无缺陷也要写“未登记”）。
- 所有证据路径可打开，`verify` 无缺失/哈希不一致。
- 报告明确列出未覆盖场景和限制。

## 效率约束

- 一个运行复用一个浏览器会话；用例间清理状态，不重复启动浏览器。
- 不把整页截图或完整快照塞进主上下文；保存路径，引用摘要。
- 同一证据只登记一次；同一状态不重复截图。
- 不为“看起来完整”而安装重复 MCP/插件。
