---
name: test-case-design
description: 从需求/验收标准设计可执行的 Web 测试用例：等价类划分、边界值、判定表、状态迁移、异常输入、业务流程、用例审查去重与需求追踪。适用于 /generate-test-cases、赛题需求分析和用例表编写。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: test-design
---

# test-case-design

先读 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。需要更细的写作/评审模板时，可组合加载已有的 `test-case-writing` 与 `test-case-reviewer`；本 Skill 负责比赛交付结构、证据关联和可执行性。

## 输入

- 需求文档、赛题说明、验收标准、原型/页面；
- 业务规则、角色权限、状态机；
- 目标 URL 与已知限制；
- 输出格式（Markdown/CSV/Excel 中间格式）。

信息不足时先给可用初版，并单列“假设/缺口”，不要编造字段或规则。

## 设计步骤

1. **功能拆解**：列出功能点、输入、动作、状态、输出、异常。
2. **输入域**：为每个输入识别有效类、无效类、空值、空白、格式错误、超长、特殊字符、注入字符。
3. **边界值**：最小值、最小值-1、最大值、最大值+1、长度 0/1/上限/上限+1、数量 0/1/多。
4. **规则组合**：多条件业务用判定表；有状态流转的用状态迁移；有角色权限的用权限矩阵。
5. **业务流程**：主流程、分支流程、回退/取消、重复提交、刷新/返回、会话过期。
6. **非功能风险**：可访问性、响应式、浏览器兼容、性能、安全输入；只设计能执行的检查。
7. **审查去重**：合并触发条件、操作、预期都相同的用例；保留需求追踪和风险标签。
8. **可执行性**：步骤具体到页面/元素/数据；预期结果是可观察状态，不写“正常显示”。

## 用例字段

| 字段 | 要求 |
|---|---|
| 用例 ID | `TC-<模块>-<三位序号>` |
| 标题 | 动作 + 对象 + 预期 |
| 优先级 | P0/P1/P2，按业务风险 |
| 需求追踪 | 需求/验收标准编号或原文锚点 |
| 前置条件 | 账号、数据、页面状态 |
| 测试数据 | 具体值；边界/异常要标明 |
| 步骤 | 编号、可复现 |
| 预期结果 | 页面文本/URL/状态/计数/提示 |
| 自动化映射 | pytest 文件/测试函数或“手工” |
| 证据要求 | 截图/快照/日志 |

## 输出

- `reports/test-cases/<slug>-test-cases.md`
- `reports/test-cases/<slug>-test-cases.csv`（便于转 Excel）
- 需求追踪矩阵与审查记录（可放在同一个 Markdown 的末尾）

## 审查清单

- [ ] 每个需求至少一条用例；高风险需求有异常/边界。
- [ ] 每个输入域有有效/无效等价类和边界。
- [ ] 有主流程、异常流程、状态回退/重复操作。
- [ ] 预期结果可观察，不依赖“看起来正常”。
- [ ] 无重复用例；合并项保留全部需求追踪。
- [ ] 未执行/无法执行的用例明确标注，不写成通过。
- [ ] 用例 ID 与 pytest `@pytest.mark.case_id` 可对应。

## 常用命令

```powershell
# 生成本地验收用例（示例）
python - <<'PY'
print('按本 Skill 的字段生成 Markdown/CSV')
PY
```

生成后请把用例文件路径、覆盖范围和缺口写回运行备注：

```powershell
python tools/evidence.py update-run --run-id <RUN_ID> --stage test-design --note "用例数=<N>; 覆盖=<模块>; 缺口=<...>"
```

## 知识加载顺序

设计用例前按以下顺序取知识，**不要**整目录通读，也不要加载已归档的旧规则：

1. `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`：阶段产物与 ID/证据命名（唯一有效）。
2. `.opencode/skills/test-design-methodology/SKILL.md` → `references/method_selector.md`：需求分诊与选方法；业务规则组合再加载 `references/test_oracle.md`。
3. `.opencode/skills/test-design-methodology/references/coverage_review.md`：提交前按覆盖项自查（此时才加载）。
4. `mooctest-knowledge/inventory/rule_registry.csv`：规则编号与弃用映射（被质疑或需追溯时读）。

确定性路由（会校验引用是否存在，缺失即非零退出）：

```powershell
python tools/knowledge_router.py --stage test-design --json
```

禁用：`knowledge/08_derived_rules/test_design_decision_rules.md`（每边界四点、方法矩阵作废）与 `knowledge/08_derived_rules/submission_schema.md`（`TC-WEB-xxx`/`SHOT-...` 命名作废）；替代路径见 `knowledge/README.md` 的归档横幅。
