---
name: test-reporting
description: 汇总测试用例、JUnit、断言、截图、日志和视觉差异，生成可追溯的 Markdown/HTML 测试报告与缺陷清单。适用于 /generate-test-report、赛题交付报告和验收报告。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: reporting
---

# test-reporting

先读 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。报告只使用 manifest、JUnit、日志和证据中的真实数据。

## 输入

- `evidence/manifest.json` 中的运行、用例、证据、缺陷；
- `reports/executions/<run>/junit-summary.json`；
- `reports/test-cases/` 的用例设计；
- `evidence/diff/<run>/` 的 `metrics.json`；
- 运行备注与已知缺口。

## 生成

```powershell
python tools/generate_report.py --run-id <RUN_ID> `
  --title "Web 应用测试执行报告"
```

产物：

- `reports/executions/<run>/report.md`
- `reports/executions/<run>/report.html`
- `reports/executions/<run>/report.json`
- `reports/defects/<run>-defects.md`

## 报告结构

1. 测试目标与范围
2. 测试环境（OS、Python、Node、浏览器、驱动、目标）
3. 测试策略与工具
4. 用例与执行结果表
5. 用例明细：步骤、预期、实际、断言、证据、日志
6. 缺陷与异常
7. 视觉差异证据
8. 证据完整性（数量、缺失、哈希）
9. 执行日志（JUnit、控制台）
10. 结论与限制

## 诚实规则

- 没有 JUnit/manifest 的结果，不写“通过”。
- `xfailed` 单列，不计入通过率；说明它是受控预期失败还是产品缺陷。
- 没有证据的用例标注“证据不完整”。
- 未执行场景写“未覆盖”，不得写成通过。
- 缺陷必须有：ID、严重度、可复现步骤、预期/实际、证据路径。
- 像素差异只写“待复核/受控变化”，不直接写缺陷。
- 不隐藏失败项；失败要写原因、影响和下一步。

## 交付前检查

```powershell
python tools/evidence.py verify --run-id <RUN_ID> --fail-on-error
python tools/evidence.py summary --run-id <RUN_ID>
python tools/evidence.py index
```

- [ ] 证据 0 缺失、0 哈希不一致。
- [ ] 每个用例至少一条证据，失败用例有截图/源码/日志。
- [ ] 报告中的截图路径可打开。
- [ ] 通过数与 JUnit 一致；xfailed 单独统计。
- [ ] 结论没有超出实际执行范围。
- [ ] 报告和缺陷清单使用同一 RUN_ID。
