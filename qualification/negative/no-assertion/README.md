# no-assertion

模拟错误：`tests/test_sample.py::test_add_valid` 被执行了，但函数体只有 `print`，
没有任何 `assert` 或 `case_ctx.check(...)`。这个用例永远是“通过”。

预期拦截：**G2** `CASE_WITHOUT_ASSERTION`（delivery_verdict=FAIL，退出码 1）。
