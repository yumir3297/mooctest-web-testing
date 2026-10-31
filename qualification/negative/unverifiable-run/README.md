# unverifiable-run

模拟错误：运行还停在 `running`，没有用例、没有 JUnit。既不能说通过，也不能说失败。

预期拦截：**G2** `EXECUTION_NOT_VERIFIABLE`（UNVERIFIED，退出码 3）。
这是 exit code 3 的真实触发路径：无法判定 ≠ 通过，也 ≠ 失败。
