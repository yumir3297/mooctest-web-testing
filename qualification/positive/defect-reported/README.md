# defect-reported  （正向样本）

场景：一个用例 failed，同时登记了一条**字段完整、已确认**的产品缺陷
（严重度+依据、类别、环境、前置条件、复现步骤、预期/实际、2 张证据截图）。

期望：
- `test_verdict=FAIL`（产品确实没通过这条用例）
- `delivery_verdict=PASS`（这批测试成果可信、可交付）
- 退出码 0

这就是“测试发现 Bug ≠ 测试成果不可信”的分界：缺陷可复现、证据齐全，
失败原因被准确定性，交付结论不受影响。

> 样本 manifest 没有写 `meta.ai_use_confirmed`：G0 会记一条 advisory UNVERIFIED，
> 只说明“AI 使用合规未声明”，不阻断本地演练，也不代表官方允许 AI。
