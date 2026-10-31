# blocked-run

模拟错误：环境/夹具阻塞，`run.status=blocked`、0 个用例、没有 JUnit。
历史审计 C5 的问题是这种运行曾经仍然 `exit 0`。

预期拦截：**G2** `RUN_STATUS_BLOCKED`（BLOCKED，退出码 2）。
阻塞运行必须非零退出，且不能被当成“通过”。
