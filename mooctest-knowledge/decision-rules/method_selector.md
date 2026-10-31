# method_selector（索引，正文已迁移）

规范文件：`../../skill-drafts/test-design-methodology/references/method_selector.md`

迁移原因：v0.2 按外部评审意见将规则正文收敛到 Skill 目录内，保证"Skill 自包含 + 单一来源"。
v0.1 内容要点（已修正）：
- 取消"参数 ≥4 → 判定表优先"的错误触发条件（现为 MS-03：由业务条件是否可枚举为规则触发）。
- 取消"每边界 min-1/min/max/max+1 四点"通用门禁（现为 MS-01：按 2-value / 3-value 覆盖项）。
- 组合覆盖补充正式出处 NIST SP 800-142（MS-05）。
- 新增 MS-00 需求分诊；MS-09 停止条件改为覆盖项口径。

本文件不可编辑；如需修改规则，请改规范文件并同步 `../../inventory/rule_registry.csv`。
