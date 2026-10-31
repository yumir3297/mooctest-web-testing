# 项目规则：mooctest-web-testing

本目录是 2026 全国大学生软件测试大赛 Web 应用测试赛道的 OpenCode 工作区。

## 1. 工作入口

- 完整闭环：`/web-test target=<URL> requirement=<path> slug=<name> scope=full`
- 就绪检查：`/web-test --check`
- 中断恢复：`/web-test --resume <RUN_ID>`

先读 `docs/WORKFLOW.md`（阶段与执行者）、`docs/CONTRACTS.md`（机器可读接口）、`docs/CONVENTIONS.md`（命名与证据）。
测试设计阶段必须加载 `test-design-methodology` Skill；阶段→知识映射用 `python tools/knowledge_router.py --stage <stage>` 查询，不要一次性读取整个知识库。

## 2. 核心规则

1. 开始测试任务前，先读 `docs/WORKFLOW.md` 与对应 Skill。
2. 不修改被测系统业务代码；只在本项目目录内创建测试、证据和报告。
3. 所有结论必须有真实执行结果支撑；禁止编造日志、截图、通过率或缺陷。
4. 截图/日志/差异必须先登记到 `evidence/manifest.json`，再在报告中引用。
5. 原始截图不可覆盖；标注图、裁剪图、差异图写入独立目录。
6. 先用 DOM/无障碍快照定位，再截图；优先元素截图。
7. Selenium 使用显式等待（`WebDriverWait`），禁止用固定 `time.sleep` 掩盖时序问题。
8. 像素差异只是复核信号，不能单独据此判定产品缺陷。
9. 不读取或泄露凭据；截图前遮蔽敏感数据。
10. 比赛前检查当届赛项对 AI 辅助工具的合规要求。

## 3. 不可绕过的门禁

1. **环境**：`python tools/env_check.py` 返回 `BLOCKED` 时不得执行测试。Chrome 与 ChromeDriver 主版本不一致即 BLOCKED。
2. **状态**：用 `python tools/pipeline.py` 推进阶段；产物不齐不得 `advance`。
3. **证据**：`python tools/evidence.py verify --run-id <RUN> --fail-on-error` 必须通过。
4. **质量**：`python tools/pre_submission_gate.py` 的 `delivery_verdict` 为 FAIL/BLOCKED/UNVERIFIED 时不得打包交付。
5. **合规**：`--official-submission` 需要先声明 AI 使用许可；未确认时只能做内部演练。

## 4. 诚实性要求

- `passed` 必须有断言或已登记证据（程序强制）。
- 未执行、不可达、缺 Oracle 的场景必须写 `NOT_RUN` / `NEEDS_ORACLE` / `不可达`，不得写成通过。
- 产品缺陷与测试系统故障必须分开陈述：`APP` 类失败要登记缺陷并取证；`ENV/LOCATOR/TIMING/DATA/SCRIPT/ASSERT` 类失败不得登记为产品缺陷。
- 受控修复每个运行最多 3 次（`tools/pipeline.py record-repair`），超限必须 `block`。
- 已知不做的能力与未验证的假设必须写进报告的限制章节。

## 5. 目录边界

| 目录 | 用途 | 规则 |
|---|---|---|
| `tests/` | TodoMVC 回归基线 | 不修改既有 3 个文件 |
| `tests/generated/<slug>/` | 新站点生成的 Page Object 与测试 | 由流水线生成，按站点隔离 |
| `fixtures/` | 本地练习应用 | 只读，不修改被测实现 |
| `evidence/` | 证据 | 只增不改；按 run 分目录 |
| `reports/` | 用例、执行报告、缺陷 | 按 run 分目录 |
| `pipeline_runs/` | 流水线状态与阶段产物 | 每 run 一目录 |
| `qualification/` | 门禁正负样本与门禁输出 | 不引用历史证据做坏样本 |
| `submission/` | 内部演练交付包 | 标记 `official_format_confirmed=false` |
| `knowledge/` | 旧知识库 | 已归档，只能作为历史追溯 |
| `mooctest-knowledge/` | 规则台账与草案源 | 只读；运行时装 `.opencode/skills/` |
