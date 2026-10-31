# FINAL — CartCheck 结算试算器 冷启动测试闭环

- 运行 ID：`RUN-20261031-COLDSTART-01`
- 目标：`http://127.0.0.1:8765/`（本地自建练习应用，仅 127.0.0.1）
- 需求：`fixtures/cartcheck/REQUIREMENTS.md`
- 范围：`full`（需求 → 用例 → 脚本 → 执行 → 归因 → 证据 → 覆盖 → 报告 → 门禁 → 交付包）
- 执行时间：2026-10-31 01:00 – 01:09（+08:00）

## 1. 结论

被测应用在 **3 条业务规则**（3 个独立根因）上与需求不符，共 5 个用例失败、5 条缺陷记录；
其余 25 个用例通过。测试成果本身可信、可复核：`delivery_verdict=PASS`，`test_verdict=FAIL`。

- 通过率：25 / (25+5) = **83.3%**（xfailed/skipped/not-run 不计入分母）
- 需求覆盖：**13/13 可测需求**均有带判据用例并已执行
- 证据：**83 条**已登记，`verify` 结果 missing=0 / mismatched=0 / cross_run=0 / duplicates=0
- 缺陷：**5 条记录 / 3 个独立根因**，全部 `reproduced`（正式执行 + 独立复现脚本各一次）
- 质量门禁：G0/G1/G2/G3/G4 全 PASS，FAIL findings = 0

## 2. 用例统计

| 维度 | 分布 |
|---|---|
| 总数 | 30（CSV 与 pytest 收集 30/30 一一对应） |
| case_type | positive 6、boundary 12、negative 9、combination 2、nonfunctional 1 |
| 执行结果 | passed 25、failed 5、blocked 0、xfailed 0、skipped 0、not-run 0 |
| 优先级 | P0 13、P1 13、P2 4 |
| 自动化 | 30/30（`tests/generated/cartcheck/test_cartcheck.py`） |

`EXPLORE` 在证据清单中是 `not-run` 的证据容器（3 条证据），不对应用例表，不计入统计。

## 3. 缺陷清单

| ID | 用例 | 标题 | 严重度 | 状态 | 复现 | 证据 |
|---|---|---|---|---|---|---|
| DEF-001 | TC-CART-002 | 银卡订单 800 元未享受 15% 折扣（门槛用了 >800） | major | open | reproduced ×2 | EV-b4ff76d876 / EV-251a55b185 / EV-7fff3e1b62 |
| DEF-002 | TC-CART-003 | 金卡 10% 折扣四舍五入：555 → 56（应 55） | major | open | reproduced ×2 | EV-196b03f496 / EV-f172e16f67 / EV-6d367d383c |
| DEF-003 | TC-CART-011 | 金卡 9998 元折扣 1000（应 999） | minor | open | reproduced ×2 | EV-b10b2ed669 / EV-0a25812b8d / EV-ee7085ab95 |
| DEF-004 | TC-CART-012 | 金卡 9999 元折扣 1000（应 999） | minor | open | reproduced ×2 | EV-7853ca95bc / EV-5bf2046869 / EV-fead5dfe76 |
| DEF-005 | TC-CART-021 | 券码大小写校验缺失：cp1234 被接受并算出 50/450 | major | open | reproduced ×2 | EV-7847d10e4a / EV-38a49db792 / EV-16852fea4e |

3 个独立根因：①银卡门槛等号判断；②折扣取整方式；③券码大小写校验。

## 4. 需求覆盖结论

| 需求 | 结论 |
|---|---|
| REQ-01 金额 1-9999 有效 | 部分通过（金额被接受，但 011/012 的折扣取整错误归 REQ-05） |
| REQ-02 金额非法拒绝 | 通过（0/10000/空/小数/非数字 5 类全部符合） |
| REQ-03 券码合法格式 | 通过（CP1234、CPABCD） |
| REQ-04 券码非法拒绝 | 未通过（长度 5/7、符号、空格、前缀均正确，小写未拒绝） |
| REQ-05 金卡 10% + floor | 未通过（001/014 通过，003/011/012 取整错） |
| REQ-06 银卡 15% + floor | 未通过（801 通过，800 无折扣） |
| REQ-07 0 折扣分支 | 通过 |
| REQ-08 积分减 1 与下限 0 | 通过 |
| REQ-09 普通会员不报错 | 通过 |
| REQ-10 E1-E7 | 未通过（E2、E3 不成立，其余 5 条成立） |
| REQ-11 第 4 节边界清单 | 部分通过（门槛等号与取整不成立） |
| REQ-12 布局与结果区可见 | 通过（scrollWidth 1239 = clientWidth 1239；三输出前后可见） |
| REQ-13 无弹窗 + 2s 可交互 | 通过（alert=0；0.084s） |

未覆盖需求：0。不可达项：`level` 第 4 个选项、`points` 第三态、券码 0–4 长度（同分区去重）、状态迁移（无状态机）。

## 5. 执行与证据

- 命令：`python tools/run_selenium.py --run-id RUN-20261031-COLDSTART-01 --target http://127.0.0.1:8765/ --suite tests/generated/cartcheck --capture-pass --reuse`
- JUnit：tests=30、failures=5、errors=0、skipped=0、xfailed=0，run_selenium 记录 elapsed=36.89s（pytest 自报 34.87s）
- 失败取证：每条失败用例均有结果区元素截图 + 视口 + 整页 + 页面源码 + 浏览器控制台日志
- 通过取证：每条通过用例有结果区元素截图 + 最终视口截图
- 证据文件：`evidence/raw/RUN-20261031-COLDSTART-01/**`、`evidence/logs/RUN-20261031-COLDSTART-01/**`
- 复现：`pipeline_runs/RUN-20261031-COLDSTART-01/repro.py` → `repro.json`，5 个场景结果与正式执行一致

## 6. 质量门禁

```
G0=PASS  G1=PASS  G2=PASS  G3=PASS  G4=PASS
delivery_verdict=PASS  test_verdict=FAIL  exit=0
summary: FAIL=0 WARNING=1 BLOCKED=0 UNVERIFIED=1 PASS=587
```

- 唯一 WARNING：`HISTORICAL_EVIDENCE_ANOMALY`（其它历史 run 的跨 run 证据，advisory，不影响本 run）。
- 唯一 UNVERIFIED：`AI_USE_UNVERIFIED`（未声明 AI 使用合规确认，本地演练不阻断）。
- 报告：`qualification/gate-runs/RUN-20261031-COLDSTART-01/gate-report.json`

## 7. 交付包

- 目录：`submission/RUN-20261031-COLDSTART-01/`
- 文件数：86（test-code 5、screenshots 72、reports 6、test-cases.xlsx、manifest.json、submission.zip）
- zip sha256：`a12107ca24a33a11a163900936ff3e9f752bb50446750551b9f19c81b9e015fd`，1,501,084 bytes
- `package_submission.py --verify`：PASS，24/24 checks，exit 0
- 标记：`official_format_confirmed=false`（内部演练包，2026 官方格式未确认）

## 8. 限制与未完成项

1. **交付包缺少 Page Object**：`tools/package_submission.py::_copy_test_code` 只收集 `tests/conftest.py`、
   `tests/pages/**`、`pytest.ini`、`requirements.txt` 与 automation 指向的测试文件，未包含
   `tests/generated/cartcheck/page_cartcheck.py`；包内 test-code 无法独立运行，需从仓库同路径补取。
   未修改打包工具（属于禁改文件），已写入 run notes 与报告限制章节。
2. **门禁需求清单格式**：`--requirements requirements.json` 会被门禁当纯文本逐行解析（`load_requirements`
   只支持 CSV/纯文本），首次尝试因此 G1 FAIL（记录在 `_attempt-requirements-json/` 与
   `g1-precheck-requirements-json.json`）。最终门禁使用内容等价的 `requirements.csv`（13 条 ID 一致）。
3. **需求缺口**：成功计算的 message 文案（G-01）、输出格式（G-03）、输入前导零/空格（G-02）未规定，
   相应行为未纳入断言；`TC-CART-030` 的 2 秒阈值起点定义为 `driver.get` 返回到按钮可点击（G-05，PARTIAL）。
4. **未做的测试**：浏览器兼容矩阵、移动端、并发、持久化、性能阈值——需求第 6 节明确为非目标。
5. **缺陷未修复**：本轮只测试不修改被测实现；5 条缺陷保持 `open`，未做修复后回归。
6. **报告生成时点**：`report.md/html/json` 生成于最终 G4 复跑之前（结论相同），交付包内的报告与仓库报告一致
   （`--force-reports` 刷新）。

## 9. 关键产物索引

| 产物 | 路径 |
|---|---|
| 需求分析 | `reports/test-cases/cartcheck-requirements.md`、`pipeline_runs/RUN-20261031-COLDSTART-01/requirements.json` |
| 用例表 | `reports/test-cases/cartcheck-test-cases.csv` / `.md` |
| 用例审查 | `pipeline_runs/RUN-20261031-COLDSTART-01/case-review.md` |
| 探索 | `reports/executions/RUN-20261031-COLDSTART-01/exploration.md`、`exploration.json` |
| 测试代码 | `tests/generated/cartcheck/test_cartcheck.py`、`page_cartcheck.py` |
| 脚本校验 | `pipeline_runs/RUN-20261031-COLDSTART-01/script-validation.json` |
| 执行结果 | `reports/executions/RUN-20261031-COLDSTART-01/junit.xml`、`junit-summary.json` |
| 归因 | `pipeline_runs/RUN-20261031-COLDSTART-01/triage.md` |
| 证据复核 | `pipeline_runs/RUN-20261031-COLDSTART-01/evidence-review.json` |
| 覆盖复核 | `pipeline_runs/RUN-20261031-COLDSTART-01/coverage.md` |
| 报告 | `reports/executions/RUN-20261031-COLDSTART-01/report.md` / `.html` / `.json`、`defects.md` |
| 门禁 | `qualification/gate-runs/RUN-20261031-COLDSTART-01/gate-report.json` |
| 交付包 | `submission/RUN-20261031-COLDSTART-01/` |

## 10. 诚实性声明

- 未执行/不可达项未计为通过；`EXPLORE` 明确标为 `not-run`（非测试用例）。
- 5 条失败均为真实断言失败，未删除断言、未跳过、未改成 xfail、未修改任何 `expected`。
- 受控修复次数：0 / 3（本轮无需修脚本）。
- 每个引用到的截图/日志都已在 `evidence/manifest.json` 登记并通过哈希校验。
- 未读取 `fixtures/cartcheck/app.js`、`index.html`、`styles.css`、`serve.py`，也未读取 `docs/coldstart/`。
