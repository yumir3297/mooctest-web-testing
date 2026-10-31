# defect-no-repro

模拟错误：一个 failed 用例挂了缺陷，但缺陷缺 `repro_steps`、`preconditions`、
`environment`——别人无法复现，也无法判断严重度是否合理。

预期拦截：**G3** `DEFECT_FIELD_MISSING`（delivery_verdict=FAIL，退出码 1）。
注意：这正是“产品缺陷 vs 不可信成果”的分界线——缺陷字段不全，交付结论不可信。
