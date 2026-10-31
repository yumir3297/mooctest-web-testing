# CartCheck 结算试算器 — 测试用例说明

- 运行：`RUN-20261031-COLDSTART-01`
- 需求：`fixtures/cartcheck/REQUIREMENTS.md`
- 机器可读用例表：`reports/test-cases/cartcheck-test-cases.csv`（30 条，UTF-8 BOM）
- 结构化用例（ORA 字段）：`pipeline_runs/RUN-20261031-COLDSTART-01/cases.json`
- 设计依据：`test-design-methodology`（MS-01/02/03/07/09、ORA-01/02/03、REV-02/03/08）+ `test-case-design`

## 1. 设计策略

| 设计方法 | 作用对象 | 覆盖项 |
|---|---|---|
| 等价类 + 3-value 边界值 | 金额（1..9999 闭区间） | 0/1/2、9998/9999/10000 |
| 等价类 + 3-value 边界值 | 金卡门槛 500、银卡门槛 800 | 499/500/501、799/800/801 |
| 格式等价类 + 错误猜测（MS-02） | 券码 `^CP[A-Z0-9]{4}$` | 长度 5/6/7；大写/数字/小写/符号/空格；前缀错 |
| 判定表（MS-03） | 金额合法性 × 券码合法性 × 等级 × 门槛 × 积分 | 9 个可达规则列（见需求分析 §4），全部命中 |
| 输出边界 | 应付金额下限 0 | 金额 1 + 积分 → 0 |
| 非功能阈值（MS-07） | 布局/可见性/弹窗/可交互时间 | 4 个数值判据 |

用例类型分布：positive 6、boundary 12、negative 9、combination 2、nonfunctional 1。
不使用状态迁移（应用无状态、无持久化，需求第 6 节明确为预期行为）。

## 2. 用例总表

| ID | 标题 | 类型 | 优先级 | 需求 | 预期（可观察值） |
|---|---|---|---|---|---|
| TC-CART-001 | 金卡满 500 享 10%：E1 | positive | P0 | REQ-10;REQ-05 | discount=50；payable=450 |
| TC-CART-002 | 银卡满 800 享 15%：E2 | positive | P0 | REQ-10;REQ-06 | discount=120；payable=680 |
| TC-CART-003 | 555 元 10% 向下取整：E3 | boundary | P0 | REQ-10;REQ-05 | discount=55；payable=500 |
| TC-CART-004 | 500 元叠加积分：E4 | positive | P0 | REQ-10;REQ-08 | discount=50；payable=449 |
| TC-CART-005 | 普通会员 1000 元：E5 | positive | P0 | REQ-10;REQ-07 | discount=0；payable=1000 |
| TC-CART-006 | 金卡 499 未达门槛：E6 | boundary | P0 | REQ-10;REQ-07;REQ-11 | discount=0；payable=499 |
| TC-CART-007 | 银卡 799 未达门槛：E7 | boundary | P0 | REQ-10;REQ-07;REQ-11 | discount=0；payable=799 |
| TC-CART-008 | 金额 0 | boundary | P0 | REQ-02;REQ-11 | message=金额需为 1-9999 的整数；discount=-；payable=- |
| TC-CART-009 | 金额 1（最小有效） | boundary | P1 | REQ-01;REQ-11 | discount=0；payable=1 |
| TC-CART-010 | 金额 2 | boundary | P2 | REQ-01;REQ-11 | discount=0；payable=2 |
| TC-CART-011 | 金额 9998 | boundary | P1 | REQ-01;REQ-05;REQ-11 | discount=999；payable=8999 |
| TC-CART-012 | 金额 9999（上边界） | boundary | P1 | REQ-01;REQ-05;REQ-11 | discount=999；payable=9000 |
| TC-CART-013 | 金额 10000 | boundary | P0 | REQ-02;REQ-11 | message=金额需为 1-9999 的整数；discount=-；payable=- |
| TC-CART-014 | 金卡 501 | boundary | P1 | REQ-05;REQ-11 | discount=50；payable=451 |
| TC-CART-015 | 银卡 801 | boundary | P1 | REQ-06;REQ-11 | discount=120；payable=681 |
| TC-CART-016 | 金额为空 | negative | P0 | REQ-02 | message=金额需为 1-9999 的整数；discount=-；payable=- |
| TC-CART-017 | 金额 500.5 | negative | P0 | REQ-02 | message=金额需为 1-9999 的整数；discount=-；payable=- |
| TC-CART-018 | 金额 abc | negative | P1 | REQ-02 | message=金额需为 1-9999 的整数；discount=-；payable=- |
| TC-CART-019 | 券码 5 位 CP123 | negative | P1 | REQ-04;REQ-11 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-020 | 券码 7 位 CP12345 | negative | P1 | REQ-04;REQ-11 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-021 | 券码小写 cp1234 | negative | P0 | REQ-04;REQ-11 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-022 | 券码符号 CP12!4 | negative | P1 | REQ-04;REQ-11 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-023 | 券码空格 CP 234 | negative | P1 | REQ-04;REQ-11 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-024 | 券码前缀 XX1234 | negative | P1 | REQ-04 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-025 | 券码 CP12 + 金卡 + 积分 | combination | P0 | REQ-04 | message=优惠券码无效；discount=-；payable=- |
| TC-CART-026 | 金额 1 + 积分 | boundary | P0 | REQ-08 | discount=0；payable=0 |
| TC-CART-027 | 普通会员 1000 + 积分 | positive | P1 | REQ-08;REQ-09 | discount=0；payable=999 |
| TC-CART-028 | 银卡 799 + 积分 | combination | P2 | REQ-07;REQ-08 | discount=0；payable=798 |
| TC-CART-029 | 券码 CPABCD（字母） | positive | P2 | REQ-03;REQ-11 | discount=50；payable=450 |
| TC-CART-030 | 布局/可见性/弹窗/2s 可交互 | nonfunctional | P1 | REQ-12;REQ-13 | scrollWidth<=clientWidth；三输出计算前后可见；alert=0；load_to_clickable<=2.0s |

完整字段（前置条件、测试数据、步骤、证据要求）见 CSV。

## 3. 需求 → 用例追溯

| 需求 | 用例 | 覆盖项说明 |
|---|---|---|
| REQ-01 | 009, 010, 011, 012 | 1..9999 有效分区：下边界 1/2、上边界 9998/9999 |
| REQ-02 | 008, 013, 016, 017, 018 | 无效分区逐类独立：0、10000、空、小数、非数字 |
| REQ-03 | 001..007, 029 | 合法券码（数字主体 + 字母主体）不产生券码错误 |
| REQ-04 | 019, 020, 021, 022, 023, 024, 025 | 长度 5/7、小写、符号、空格、前缀、优先级 |
| REQ-05 | 001, 003, 011, 012, 014 | 10% + floor，含 999.8/999.9/50.1 三处取整证据 |
| REQ-06 | 002, 015 | 15% + floor（120.15） |
| REQ-07 | 005, 006, 007, 028 | 普通会员与未达门槛均为 0 |
| REQ-08 | 004, 026, 027, 028 | 减 1 生效、下限 0、与无折扣叠加 |
| REQ-09 | 027 | 普通会员不报错（无两种错误文案） |
| REQ-10 | 001..007 | E1-E7 逐条一条用例 |
| REQ-11 | 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 019, 020, 021, 022, 023, 029 | 第 4 节边界清单逐项 |
| REQ-12 | 030 | scrollWidth/clientWidth + 三输出可见性 |
| REQ-13 | 030 | alert 计数 + 2s 可交互阈值 |

## 4. 覆盖项核对（REV-02）

| 覆盖项 | 取值 | 命中用例 |
|---|---|---|
| 金额下边界（3-value） | 0 / 1 / 2 | 008 / 009 / 010 |
| 金额上边界（3-value） | 9998 / 9999 / 10000 | 011 / 012 / 013 |
| 金卡门槛（3-value） | 499 / 500 / 501 | 006 / 001 / 014 |
| 银卡门槛（3-value） | 799 / 800 / 801 | 007 / 002 / 015 |
| 券码长度 | 5 / 6 / 7 | 019 / 001-007,029 / 020 |
| 券码字符集 | 大写 / 数字 / 小写 / 符号 / 空格 | 029 / 001 / 021 / 022 / 023 |
| 金额非法分区 | 空 / 小数 / 非数字 / 0 / >9999 | 016 / 017 / 018 / 008 / 013 |
| 输出下边界 0 | 0 / 1 | 026 / 009 |
| 判定表可达列 | 9 列 | 008-018（列1）、019-025（列2/9）、001/003/011/012/014（列3）、002/015（列4）、005/009/010（列5）、006/007（列6）、004/026/027/028（列7）、027（列8） |
| 非功能阈值 | 4 项 | 030 |

不可达 / 不适用的覆盖项：

| 项 | 原因 |
|---|---|
| `level` 枚举第 4 个值 | 页面只有 regular/silver/gold 三个选项，需求未定义非法值 → 不可达 |
| `points` 三态 | checkbox 只有勾选/未勾选 → 不适用 |
| 券码长度 0/1/2/3/4 的每一长度 | 需求第 4 节只要求 5/6/7；其余长度与「长度≠6」同分区，不重复造用例（REV-03 去重） |
| 状态迁移覆盖 | 无状态机（无持久化、无多步流程）→ 不适用 |

## 5. 假设与缺口（与需求分析一致）

| # | 内容 | 处理 |
|---|---|---|
| G-01 | 成功计算的 message 文案未规定 | 成功用例不断言 message 文本；只有错误用例断言字面文案 |
| G-02 | 前导零、`+500`、前后空格未定义 | 不生成用例（不编造规则） |
| G-03 | 输出格式（千分位/小数）未规定 | 断言前把文本规范化为整数再比较；探索已确认输出为纯整数 |
| G-05 | 「2 秒内可交互」起点未定义 | 采用 get→按钮可点击，阈值 2.0s，标 ORACLE-PARTIAL |

## 6. 执行状态

设计阶段全部为 `NOT_RUN`（见 CSV `status` 列）。执行后按真实结果更新 `status` / `actual` / `executed_in_run`，失败用例进入 `triage.md` 归因，不修改预期。
