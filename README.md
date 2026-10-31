# mooctest-web-testing

面向全国大学生软件测试大赛 **Web 应用测试赛道**的 AI Agent 自动化测试系统（OpenCode）。

从「一个新站点的 URL + 需求文档」出发，自动完成：

```text
环境门禁 → 知识加载 → 需求分诊 → 浏览器探索 → 用例设计 → 用例审查
→ 脚本生成 → 脚本校验 → 执行 → 失败归因 → 证据复核 → 覆盖复核
→ 报告 → 质量门禁 → 内部交付包 → 2025 官方格式导出
```

---

## 1. 当前状态（2026-10-31）

| 目标 | 判定 | 关键证据 |
|---|---|---|
| A. 新站点自主测试闭环 | **PASS**（本地受控） | 冷启动 `RUN-20261031-COLDSTART-01`：17/17 阶段、30 用例、25 passed / 5 failed、5 缺陷 / 3 根因、83/83 证据 |
| B. 知识蒸馏与 Skill 接入 | **PASS** | `test-design-methodology` 运行时可加载；11 阶段确定性路由；BVA 从「四点法」改为 2-value/3-value |
| C. 质量自检与内部交付 | **PASS** | G0–G5 六层门禁；12 个负向样本全被阻断；交付包 24/24 且可独立复跑 |
| 2025 官方格式 | **已适配并实测** | 10 列用例表、`<App>_R001_001` 编号、`<11位时间戳>_<编号>.png` 截图、一需求一函数 |
| 2026 官方规则 | **已整理培训视频** | 评分维度、提交格式、环境要求见 `docs/COMPETITION_RULES_2026.md`；2026 赛题包与 AI 许可仍未获取 |
| Python 运行环境 | **READY** | `env_check` 17/17；官方版本组合 Selenium 4.49.0 + pytest 8.4.2 回归 7 passed + 1 xfailed，15/15 证据 |
| AI 使用许可 | **部分确认** | 2025 携程机票练习赛《注意事项》明文允许用大模型生成用例与代码；2026 未确认 |

完整验收报告见 [`docs/ACCEPTANCE_REPORT_20261031.md`](docs/ACCEPTANCE_REPORT_20261031.md)。

---

## 2. 先读这几份

| 想了解 | 读 |
|---|---|
| 整体架构与数据流 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| 工作流阶段、执行者、产物 | [`docs/WORKFLOW.md`](docs/WORKFLOW.md) |
| 模块间机器可读接口契约 | [`docs/CONTRACTS.md`](docs/CONTRACTS.md) |
| 2025 官方规范与差异对照 | [`docs/OFFICIAL_2025.md`](docs/OFFICIAL_2025.md) |
| 2026 官方培训视频规则整理 | [`docs/COMPETITION_RULES_2026.md`](docs/COMPETITION_RULES_2026.md) |
| 环境与工具链基线 | [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) |
| 第一次实测交接单 | [`docs/HANDOFF_FIRST_TEST.md`](docs/HANDOFF_FIRST_TEST.md) |
| 质量门禁设计 | [`docs/REPORTING.md`](docs/REPORTING.md) |
| 工程进度与模块所有权 | [`docs/PROGRESS.md`](docs/PROGRESS.md) |
| 冷启动隐藏验收基准 | [`docs/coldstart/HIDDEN_EXPECTATIONS.md`](docs/coldstart/HIDDEN_EXPECTATIONS.md) |
| 冷启动实测结果 | [`reports/executions/RUN-20261031-COLDSTART-01/report.md`](reports/executions/RUN-20261031-COLDSTART-01/report.md) |

---

## 3. 代码地图

```text
tools/
  env_check.py              环境门禁（READY / BLOCKED，退出码 0 / 2）
  knowledge_router.py       11 阶段知识路由（缺引用即非零退出）
  pipeline.py               17 阶段状态机 + 产物门禁 + 3 次修复预算
  scaffold.py               用例表 → Page Object / pytest 骨架
  run_selenium.py           pytest 执行 + JUnit + 环境快照 + 超时强杀
  evidence.py               manifest v1.1（SHA-256、跨 run 检测、缺陷字段）
  visual_diff.py            截图差异 / 区域 / 标注
  generate_report.py        12 节报告（MD + HTML + JSON）
  pre_submission_gate.py    G0–G5 双结论门禁
  package_submission.py     内部交付包 + --verify
  export_official_2025.py   2025 官方格式导出 + 结构校验
  publish_repo.py           生成脱敏的可发布快照
  validators/               G0–G5 分域校验器

tests/                      TodoMVC 回归基线（受保护，哈希不变）
tests_meta/                 质量门禁自测（22 项）
tests_meta_report/          报告与打包自测（12 项）
fixtures/cartcheck/         冷启动用的本地练习应用（含 3 个植入缺陷）
qualification/              门禁正负样本（12 负向 + 2 正向）
```

---

## 4. 统一入口

```powershell
# 就绪检查
/web-test --check

# 完整闭环
/web-test target=<URL> requirement=<path> slug=<name> scope=full

# 中断恢复
/web-test --resume <RUN_ID>
```

等价的命令行（部分）：

```powershell
python tools/env_check.py --json
python tools/knowledge_router.py --stage test-design --json
python tools/pipeline.py init --run-id RUN-X --target <URL> --requirement <PATH> --slug <SLUG>
python tools/scaffold.py --slug <SLUG> --target <URL> --cases <CSV> --out tests/generated/<SLUG>
python tools/run_selenium.py --run-id RUN-X --target <URL> --suite tests/generated/<SLUG>
python tools/evidence.py verify --run-id RUN-X --fail-on-error
python tools/generate_report.py --run-id RUN-X
python tools/pre_submission_gate.py --run-id RUN-X --cases <CSV> --junit-summary <JSON> \
  --submission submission/RUN-X --official-2025 official_2025/RUN-X
python tools/package_submission.py --run-id RUN-X --json
python tools/export_official_2025.py --run-id RUN-X --app <App> --cases <CSV> --with-runner
```

---

## 5. 质量门禁的双结论

- `test_verdict`：被测应用是否通过测试。
- `delivery_verdict`：这批测试成果是否可信、可交付。

真实产品缺陷会让 `test_verdict=FAIL`，但只要缺陷已确认并取证，`delivery_verdict` 仍可为 `PASS`。门禁拦的是「不可信的成果」，不是「被测系统有 Bug」。

---

## 6. 本仓库的边界

**不含**以下内容（保留在本地工作区）：

- 官方赛题包与组委会材料（`materials/`，176MB，公开传播有版权风险）
- 教材 PDF（`booook/`，含第三方来源标识）
- 浏览器驱动二进制、`node_modules`、构建缓存
- 原始压缩包与 `.xlsx` 交付件

**已做脱敏**：本机用户名、绝对路径已替换为 `<user>` / `<PROJECT_ROOT>`；因此部分报告里的路径与本地原始日志不完全一致，属于预期。

**未验证**：2026 赛题包与提交模板、慕测平台真实比赛环境、AI 使用许可。2026 评分维度与提交格式已从官方培训视频整理，但属于视频画面整理，不是官方文件。

> 内部系统集成验收通过 ≠ 已获得正式竞赛 AI 使用许可或官方交付格式认证。
