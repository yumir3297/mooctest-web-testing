# empty-cases

模拟错误：执行记录看起来完整（1 个 passed 用例、JUnit 1 passed、证据齐全），
但用例表只有表头，没有任何用例。

预期拦截：**G1** `CASES_EMPTY`（delivery_verdict=FAIL，退出码 1）。
用例集为空时，“测试通过”无法被任何设计覆盖支撑。
