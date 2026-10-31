# 覆盖复核（COVERAGE_REVIEW）

- 运行：`RUN-20261031-COLDSTART-01`
- 用例表：`reports/test-cases/cartcheck-test-cases.csv`（30 条，全部 `executed_in_run=RUN-20261031-COLDSTART-01`）
- 执行结果：`reports/executions/RUN-20261031-COLDSTART-01/junit-summary.json`（tests=30, failures=5, errors=0, skipped=0, xfailed=0）
- 证据：`evidence/manifest.json`，`evidence.py verify` → checked=83 / ok=83 / missing=0 / mismatched=0 / cross_run=0

## 1. 覆盖摘要（REV-00 / REV-09）

| 指标 | 值 | 说明 |
|---|---|---|
| 可测需求总数（分母） | 13 | REQ-01..REQ-13 |
| 有判据用例覆盖的需求 | 13 | REQ-03 仅 1 条用例（029）但判据完整 |
| 需求关联度 | 13/13 = 100% | 每条需求至少 1 条用例引用 |
| 可验证用例覆盖率 | 13/13 = 100% | 全部用例带 SPEC/DERIVED/PARTIAL 判据，无 UNKNOWN |
| 已执行用例 | 30/30 = 100% | 无 NOT_RUN、无 skipped、无 blocked |
| 通过 / 失败 | 25 / 5 | 通过率 = 25/(25+5) = 83.3%（xfailed/skipped 不参与） |
| 覆盖项达成 | 9/9 组 | 详见用例文档 §4 |
| 虚构预期 | 0 | 每条 expected 可指回需求或推导链 |
| 缺陷 | 5 条记录 / 3 个独立根因 | DEF-001..DEF-005 |

## 2. 需求 → 用例 → 结果 → 证据

| 需求 | 用例 | 执行结果 | 首要证据 |
|---|---|---|---|
| REQ-01 | TC-CART-009 | passed | EV-ef743656d3 |
| REQ-01 | TC-CART-010 | passed | EV-afdc596fad |
| REQ-01 | TC-CART-011 | failed | EV-b10b2ed669 |
| REQ-01 | TC-CART-012 | failed | EV-7853ca95bc |
| REQ-02 | TC-CART-008 | passed | EV-192f4bf535 |
| REQ-02 | TC-CART-013 | passed | EV-09c27f6edc |
| REQ-02 | TC-CART-016 | passed | EV-56fa262ed6 |
| REQ-02 | TC-CART-017 | passed | EV-42b7114bb3 |
| REQ-02 | TC-CART-018 | passed | EV-bc8da73870 |
| REQ-03 | TC-CART-029 | passed | EV-13438dcdbc |
| REQ-04 | TC-CART-019 | passed | EV-df86048c4e |
| REQ-04 | TC-CART-020 | passed | EV-bd891df993 |
| REQ-04 | TC-CART-021 | failed | EV-7847d10e4a |
| REQ-04 | TC-CART-022 | passed | EV-d3aea220fe |
| REQ-04 | TC-CART-023 | passed | EV-7cd49c7027 |
| REQ-04 | TC-CART-024 | passed | EV-4b31c28034 |
| REQ-04 | TC-CART-025 | passed | EV-b0f8b15d31 |
| REQ-05 | TC-CART-001 | passed | EV-302193cec1 |
| REQ-05 | TC-CART-003 | failed | EV-196b03f496 |
| REQ-05 | TC-CART-011 | failed | EV-b10b2ed669 |
| REQ-05 | TC-CART-012 | failed | EV-7853ca95bc |
| REQ-05 | TC-CART-014 | passed | EV-19f2df71cd |
| REQ-06 | TC-CART-002 | failed | EV-b4ff76d876 |
| REQ-06 | TC-CART-015 | passed | EV-1210e9f882 |
| REQ-07 | TC-CART-005 | passed | EV-f6177a66c3 |
| REQ-07 | TC-CART-006 | passed | EV-cfa6bb682e |
| REQ-07 | TC-CART-007 | passed | EV-e2e4af1758 |
| REQ-07 | TC-CART-028 | passed | EV-03bd5d245c |
| REQ-08 | TC-CART-004 | passed | EV-81421592c5 |
| REQ-08 | TC-CART-026 | passed | EV-701f26169a |
| REQ-08 | TC-CART-027 | passed | EV-4699f09496 |
| REQ-08 | TC-CART-028 | passed | EV-03bd5d245c |
| REQ-09 | TC-CART-027 | passed | EV-4699f09496 |
| REQ-10 | TC-CART-001 | passed | EV-302193cec1 |
| REQ-10 | TC-CART-002 | failed | EV-b4ff76d876 |
| REQ-10 | TC-CART-003 | failed | EV-196b03f496 |
| REQ-10 | TC-CART-004 | passed | EV-81421592c5 |
| REQ-10 | TC-CART-005 | passed | EV-f6177a66c3 |
| REQ-10 | TC-CART-006 | passed | EV-cfa6bb682e |
| REQ-10 | TC-CART-007 | passed | EV-e2e4af1758 |
| REQ-11 | TC-CART-006 | passed | EV-cfa6bb682e |
| REQ-11 | TC-CART-007 | passed | EV-e2e4af1758 |
| REQ-11 | TC-CART-008 | passed | EV-192f4bf535 |
| REQ-11 | TC-CART-009 | passed | EV-ef743656d3 |
| REQ-11 | TC-CART-010 | passed | EV-afdc596fad |
| REQ-11 | TC-CART-011 | failed | EV-b10b2ed669 |
| REQ-11 | TC-CART-012 | failed | EV-7853ca95bc |
| REQ-11 | TC-CART-013 | passed | EV-09c27f6edc |
| REQ-11 | TC-CART-014 | passed | EV-19f2df71cd |
| REQ-11 | TC-CART-015 | passed | EV-1210e9f882 |
| REQ-11 | TC-CART-019 | passed | EV-df86048c4e |
| REQ-11 | TC-CART-020 | passed | EV-bd891df993 |
| REQ-11 | TC-CART-021 | failed | EV-7847d10e4a |
| REQ-11 | TC-CART-022 | passed | EV-d3aea220fe |
| REQ-11 | TC-CART-023 | passed | EV-7cd49c7027 |
| REQ-11 | TC-CART-029 | passed | EV-13438dcdbc |
| REQ-12 | TC-CART-030 | passed | EV-a3d843928e |
| REQ-13 | TC-CART-030 | passed | EV-a3d843928e |

（每条用例另有 1 张结果区元素截图；失败用例额外有视口/整页/页面源码/浏览器日志，见 manifest。）

## 3. 逐需求结论

| 需求 | 结论 | 依据 |
|---|---|---|
| REQ-01 金额 1-9999 有效 | 部分通过 | 009/010 通过；011/012 的金额被接受但折扣取整错误（失败点归 REQ-05），故「有效输入被接受」成立，「该分支金额正确」不成立 |
| REQ-02 金额非法拒绝 | **通过** | 008/013/016/017/018 全部得到规定文案且两项为 `-` |
| REQ-03 券码合法格式 | **通过** | 029（CPABCD）与 E1-E7 的 CP1234 均未被券码校验拒绝 |
| REQ-04 券码非法拒绝 | **未通过** | 019/020/022/023/024/025 通过；021（含小写）未被拒绝 → DEF-005 |
| REQ-05 金卡 10% + floor | **未通过** | 001/014 通过；003/011/012 取整错误 → DEF-002/003/004 |
| REQ-06 银卡 15% + floor | **未通过** | 015（801）通过；002（800）无折扣 → DEF-001 |
| REQ-07 0 折扣分支 | **通过** | 005/006/007/028 全部符合 |
| REQ-08 积分减 1 与下限 0 | **通过** | 004/026/027/028 全部符合（026 验证下限 0） |
| REQ-09 普通会员不报错 | **通过** | 027 无错误文案，金额 0/999 正确 |
| REQ-10 E1-E7 逐条成立 | **未通过** | E1/E4/E5/E6/E7 成立，E2、E3 不成立 → DEF-001/002 |
| REQ-11 第 4 节边界清单 | 部分通过 | 金额边界 0/1/2/9998/9999/10000 均按边界语义处理（0/10000 拒绝、其余接受），金/银门槛下侧正确，券长 5/7 与符号/空格拒绝正确；门槛等号（500 通过、800 失败）与取整（9998/9999）不成立 → DEF-001..004 |
| REQ-12 布局与结果区可见 | **通过** | TC-CART-030：scrollWidth 1254 ≤ clientWidth 1254；三个输出元素计算前后均 displayed=true |
| REQ-13 无弹窗 + 2s 可交互 | **通过** | alert 计数 0、无原生对话框；load→clickable 实测 0.063–0.077 s（阈值 2.0 s） |

## 4. 未覆盖需求

无。13 条可测需求全部有至少一条带判据的用例并已执行。

`非测试范围`（需求第 6 节）：真实支付、后端连接、登录权限、浏览器兼容矩阵、性能阈值、并发、持久化——按需求排除，不计入分母。

## 5. 未执行用例

无。CSV 30 条全部 `passed` 或 `failed`，`executed_in_run` 均为本 run。

`EXPLORE` 在证据清单中登记为 `not-run`：它是探索阶段的证据容器（3 条证据），不对应 CSV 用例，不参与执行统计与通过率。

## 6. 不可达 / 不适用项

| 项 | 原因 |
|---|---|
| `level` 第 4 个选项（非法等级） | 页面仅 `regular`/`silver`/`gold`，需求未定义非法值 → 不可达 |
| `points` 第三态 | checkbox 只有勾选/未勾选 → 不适用 |
| 券码长度 0–4 逐长度 | 与「长度≠6」同分区，按 REV-03 去重，不重复造用例 |
| 状态迁移覆盖 | 应用无状态机、无持久化（需求第 6 节） → 不适用 |
| 金额前导零、`+500`、前后空格 | 需求未定义（缺口 G-02），不生成正式用例，避免编造规则 |
| 成功计算时的 message 文案 | 需求未规定（缺口 G-01），成功用例不断言 message |
| 输出格式（千分位/小数） | 需求未规定（缺口 G-03），断言按整数文本归一化比较 |

## 7. 覆盖缺口对结论的影响

- 5 条失败集中在两条业务规则上：**取整方式**（3 条）与 **银卡等号门槛**（1 条），外加 **券码大小写校验**（1 条）。
- 其余 25 条用例覆盖了金额校验、券码格式的长/前缀/符号/空格、普通会员、未达门槛、积分叠加与下限、布局与交互时限，全部符合需求。
- 因此本 run 的结论是「应用在 3 条规则上不符合需求」，而不是「应用整体不可用」；未覆盖项仅为需求未定义的行为，不构成隐藏风险。

## 8. 与报告/门禁的一致性

- 本文件的用例计数与 `junit-summary.json`（30/5/0/0）一致；
- 证据 ID 均可在 `evidence/manifest.json` 中查到，`verify` 结果为 0 missing / 0 mismatched / 0 cross_run；
- 缺陷 DEF-001..DEF-005 均挂在对应失败用例下，`triage.md` 有分类与依据。
