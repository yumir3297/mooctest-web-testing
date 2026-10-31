# 失败归因（FAILURE_TRIAGE）

- 运行：`RUN-20261031-COLDSTART-01`
- 执行：`python tools/run_selenium.py --run-id RUN-20261031-COLDSTART-01 --target http://127.0.0.1:8765/ --suite tests/generated/cartcheck --capture-pass --reuse`
- JUnit：`reports/executions/RUN-20261031-COLDSTART-01/junit-summary.json` → tests=30, failures=5, errors=0, skipped=0, xfailed=0, elapsed=36.89s
- 受控修复预算：**0 / 3 次**（`pipeline.py record-repair` 未使用）

## 1. 归因表

| 用例 | 期望（需求） | 实际（页面） | 分类 | 依据 | 处置 |
|---|---|---|---|---|---|
| TC-CART-002 | discount=120；payable=680（R3 silver≥800 → 15%，E2） | discount=0；payable=800；message=空 | **APP** | 需求第 3 节 E2 与 R3 明文给出 800 元应享 15%。同规则在 801 元（TC-CART-015）正常输出 120/681，差异只在等号本身 → 实现门槛写为 `>800` | 登记 DEF-001（major）；不改预期 |
| TC-CART-003 | discount=55；payable=500（E3，555×0.1=55.5 floor） | discount=56；payable=499 | **APP** | R3「优惠金额一律向下取整到整元（不得四舍五入）」；55.5 被判为 56，系四舍五入 | 登记 DEF-002（major）；不改预期 |
| TC-CART-011 | discount=999；payable=8999（9998×0.1=999.8 floor） | discount=1000；payable=8998 | **APP** | 同 R3 取整口径；999.8 被判为 1000 | 登记 DEF-003（minor，同根因）；不改预期 |
| TC-CART-012 | discount=999；payable=9000（9999×0.1=999.9 floor） | discount=1000；payable=8999 | **APP** | 同 R3 取整口径；999.9 被判为 1000 | 登记 DEF-004（minor，同根因）；不改预期 |
| TC-CART-021 | message=优惠券码无效；discount=-；payable=-（R2 `^CP[A-Z0-9]{4}$`） | message=空；discount=50；payable=450 | **APP** | R2 明确小写属非法字符集；页面接受 `cp1234` 并完成折扣计算，券码校验被绕过 | 登记 DEF-005（major）；不改预期 |

未出现 `ENV` / `LOCATOR` / `TIMING` / `DATA` / `SCRIPT` / `ASSERT` / `UNKNOWN` 类失败：
- 30 个用例全部完成真实交互，无超时、无元素定位异常、无环境错误；
- 每条失败都在断言处抛出，实际值与页面渲染值一致（元素截图可见），说明等待与定位均正常；
- 断言文本直接来自需求原文，没有为了让用例通过而修改过任何 `expected`（本轮 `expected` 从未改动）。

## 2. 失败状态字段的修正

`tests/conftest.py` 对任何断言失败统一写入 `meta.failure_class="ASSERT"`（它无法区分产品缺陷与断言写错）。
归因完成后用 `evidence.py update-case --meta failure_class=APP` 把上述 5 条改为 `APP`，与本节结论一致；
未修改 conftest，也未修改任何断言或预期。

## 3. 缺陷登记（`evidence.py add-defect`）

| 缺陷 | 用例 | 标题 | 严重度 | 状态 | 复现 | 证据 |
|---|---|---|---|---|---|---|
| DEF-001 | TC-CART-002 | 银卡订单 800 元未享受 15% 折扣：门槛判断使用 >800 而非 >=800 | major | open | reproduced ×2 | EV-b4ff76d876（结果区元素截图）、EV-251a55b185（失败视口）、EV-7fff3e1b62（独立复现截图） |
| DEF-002 | TC-CART-003 | 金卡 10% 折扣采用四舍五入而非向下取整：555 元得 56（应 55） | major | open | reproduced ×2 | EV-196b03f496、EV-f172e16f67、EV-6d367d383c |
| DEF-003 | TC-CART-011 | 金卡 9998 元折扣四舍五入为 1000（应 999） | minor | open | reproduced ×2 | EV-b10b2ed669、EV-0a25812b8d、EV-ee7085ab95 |
| DEF-004 | TC-CART-012 | 金卡 9999 元折扣四舍五入为 1000（应 999） | minor | open | reproduced ×2 | EV-7853ca95bc、EV-5bf2046869、EV-fead5dfe76 |
| DEF-005 | TC-CART-021 | 优惠券码大小写校验缺失：cp1234 被接受并完成折扣计算 | major | open | reproduced ×2 | EV-7847d10e4a、EV-38a49db792、EV-16852fea4e |

复现方式：正式执行（pytest）+ `pipeline_runs/RUN-20261031-COLDSTART-01/repro.py` 独立浏览器会话，
两次结果一致（`repro.json`），故 `repro_status=reproduced`、`repro_count=2`。

根因归并说明：DEF-002/003/004 是同一「取整方式」缺陷在三个取值上的表现，按要求每个失败用例都要有可追溯缺陷记录，
因此在各自用例下分别登记，并在描述中互相引用；统计缺陷总数时按 **3 个独立根因**（门槛等号、取整方式、券码大小写）理解。

## 4. 修复与重跑

- 本轮 5 条失败全部为产品行为与需求不符，脚本、定位、等待、数据均无问题，因此**没有修改测试代码**，也**不需要重跑**：
  `--keyword` 定向重跑的前提是脚本被修复，这里没有修复动作。
- 未删除断言、未跳过用例、未使用 `xfail`、未放宽任何预期。
- 受控修复预算仍为 0/3。

## 5. 工具限制（与产品无关）

1. `tools/validators/cases.load_requirements` 只支持 CSV（`requirement_id` 列）或纯文本需求清单，**不解析 JSON**。
   按任务书把 `--requirements .../requirements.json` 传入时，门禁把 JSON 逐行当纯文本，得到 `[`、`{`、`"id":` 等伪需求 ID，
   G1 报 `REQUIREMENT_UNKNOWN` + `REQUIREMENT_NOT_COVERED`（见 `pipeline_runs/RUN-20261031-COLDSTART-01/g1-precheck-requirements-json.json`）。
   这不是用例表缺陷。处置：保留 `requirements.json` 作为阶段产物，另生成内容等价的 `requirements.csv`
   （`build_requirements_csv.py`，13 条 ID 完全一致），门禁改用 CSV 输入。
2. `tools/pipeline.py init` 不接受 `--authorized` 参数，授权说明改落盘为 `authorization.md`。
3. `tests/conftest.py` 的失败分类固定写 `ASSERT`，已按 §2 修正元数据，未改文件本身。

## 6. 归因结论

- APP 类失败：5 条 → 5 个缺陷记录（3 个独立根因），全部可复现、有证据、有严重度依据。
- 非产品类失败：0 条。
- 未归因失败：0 条。
- 通过：25 条。
