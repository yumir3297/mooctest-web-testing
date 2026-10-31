# no-boundary-coverage

模拟错误：用例表有 positive / negative，但没有 boundary 用例（类型列改成 state）。

预期拦截：**G1** `CASE_TYPE_COVERAGE_MISSING`（delivery_verdict=FAIL，退出码 1）。
