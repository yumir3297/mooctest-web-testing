# qualification — 质量门禁的正负样本

本目录只存放 **门禁自身的验证材料**，不引用、不修改真实历史证据
（`evidence/manifest.json` 只被读取，运行前后哈希不变）。

## 目录

```text
qualification/
├── make_samples.py          生成全部样本（可重复执行）
├── run_all.py               对全部样本跑一遍门禁并输出汇总表
├── negative/                必须被拦截的样本（12 个）
├── positive/                必须可交付的样本（2 个）
├── package-sample/          G4 交付包样本（good / broken）
└── gate-runs/               每次真实执行的门禁输出（gate-report.json）
```

每个样本都是“小型伪项目”，自带 `manifest.json` / `cases.csv` /
`junit-summary.json` / `junit.xml` / `tests/` / `evidence/` / `README.md`。
样本的证据文件（Pillow 生成的 PNG、日志）都在样本自己的
`evidence/` 子目录下，**从未登记进真实 manifest**。

## 运行方式

```bash
python qualification/make_samples.py          # 重新生成样本
python -m pytest tests_meta -q                # 门禁自身的 22 个测试
python qualification/run_all.py               # 全样本跑一遍，输出表格
python tools/pre_submission_gate.py --help    # 门禁 CLI
```

## 判定口径（与 docs/CONTRACTS.md §4 一致）

| 结论 | 含义 |
|---|---|
| `test_verdict` | 被测应用本身是否通过；真实产品缺陷会让它是 `FAIL` |
| `delivery_verdict` | 这批测试成果是否可信、可交付；已确认并取证的缺陷**不会**拉低它 |

- `delivery_verdict=PASS/WARNING` → 退出码 0
- `FAIL` → 1，`BLOCKED` → 2，`UNVERIFIED` → 3
- `advisory` findings 只记录，不参与 verdict；`--official-submission` 会把
  合规类 advisory（AI 使用未声明）升级为 `BLOCKED`。
