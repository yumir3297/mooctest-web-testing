# suspected-defect  （正向样本）

场景同 `defect-reported`，但缺陷状态是 `suspected`（尚未复核）。

期望：
- `test_verdict=FAIL`
- `delivery_verdict=WARNING`（允许交付，但报告必须标注结论不确定）
- 退出码 0
- findings 中包含 `DEFECT_STATUS_UNCONFIRMED`（WARNING）

门禁不会把 `suspected` 自动升级成 `confirmed`。
