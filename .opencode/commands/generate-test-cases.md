---
description: 从需求生成等价类/边界值/异常/业务流程测试用例并审查去重
agent: build
---

目标：$ARGUMENTS

先加载 `test-case-design` Skill，并读取 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。

## 参数约定

- `requirement=<path>` 或 `requirement=<URL>`：需求来源。
- `module=<name>`：模块名，用于文件名与用例 ID。
- `format=md|csv|both`：默认 both。
- `--check`：只检查输出目录、模板和依赖，不生成内容。

## 步骤

1. `--check`：确认 `reports/test-cases/` 可写、`docs/CONVENTIONS.md` 存在，输出 `TEST_CASE_READY` 并停止。
2. 读取需求，列出功能点、输入域、状态、业务规则、验收标准；信息缺口单列“假设”。
3. 为每个输入域设计有效/无效等价类、边界值（0/1/上限/上限+1）、异常输入（空、空白、格式错、超长、特殊字符/注入）。
4. 对多条件规则用判定表；对状态流转用状态迁移；对角色权限用权限矩阵。
5. 设计主流程、分支、回退/取消、重复提交、刷新/返回。
6. 生成用例表：ID、标题、优先级、需求追踪、前置条件、数据、步骤、预期、自动化映射、证据要求。
7. 审查：合并重复项、补覆盖缺口、标注手工/未执行项；不得把未执行写成通过。
8. 输出到 `reports/test-cases/<module>-test-cases.md` 与 `.csv`；在运行备注中记录用例数、覆盖范围、缺口。
9. 输出摘要：用例总数、P0/P1 数量、正常/异常/边界数量、未覆盖项。
