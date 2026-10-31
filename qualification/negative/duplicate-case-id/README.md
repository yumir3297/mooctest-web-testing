# duplicate-case-id

模拟错误：`TC-SAMPLE-001` 在同一个用例表中出现两次，用例身份不唯一，
证据与执行结果无法对应到唯一条目。

预期拦截：**G1** `CASE_ID_DUPLICATE`（delivery_verdict=FAIL，退出码 1）。
