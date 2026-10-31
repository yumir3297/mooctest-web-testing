# junit-manifest-mismatch

模拟错误：manifest 记 5 个用例 passed，但 JUnit 只跑了 3 个（summary 与 xml 都是 3）。
pytest 退出码是 0，单看退出码完全看不出来。

预期拦截：**G2** `JUNIT_MANIFEST_COUNT_MISMATCH` 与 `MANIFEST_PASSED_WITHOUT_JUNIT`
（delivery_verdict=FAIL，退出码 1）。
