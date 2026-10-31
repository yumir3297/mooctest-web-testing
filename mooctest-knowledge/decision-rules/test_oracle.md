# test_oracle（索引，正文已迁移）

规范文件：`../../skill-drafts/test-design-methodology/references/test_oracle.md`

v0.1 → v0.2 主要修正：
- 新增 §0：**判据证据强度**（Oracle Type）与**执行状态**（NOT_RUN/PASS/FAIL/BLOCKED/INCONCLUSIVE）两个正交维度，分字段保存。
- `ORACLE-UNKNOWN` 不再允许出现在正式用例集，统一转 `observations.json`，且不计入可验证覆盖率。
- 新增 ORA-09：失败四类归因（业务缺陷/脚本错误/环境错误/规格歧义），禁止为让用例通过而改预期。
- 新增 §2 双指标（需求关联度 / 可验证用例覆盖率）与"虚构预期数必须为 0"。

本文件不可编辑。
