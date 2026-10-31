# bad-sha256

模拟错误：证据 PNG 是真实文件（在 `qualification/` 下生成，未登记进真实 manifest），
但 manifest 里的 sha256 被改成 `0000...`，模拟证据被替换/篡改。

预期拦截：**G3** `EVIDENCE_HASH_MISMATCH`（delivery_verdict=FAIL，退出码 1）。
哈希校验直接复用 `tools/evidence.py` 的 `verify_evidence()`。
