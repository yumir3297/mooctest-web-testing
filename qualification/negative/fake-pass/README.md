# fake-pass

模拟错误：manifest 写 3 个用例 passed，但根本没有 JUnit 摘要和 JUnit XML。
pytest 从没跑过，通过结论是手写的。

预期拦截：**G2** `JUNIT_SUMMARY_MISSING`（delivery_verdict=FAIL，退出码 1）。
