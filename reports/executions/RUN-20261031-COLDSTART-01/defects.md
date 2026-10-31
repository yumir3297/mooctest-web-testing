# 缺陷清单 RUN-20261031-COLDSTART-01

## DEF-001 银卡订单 800 元未享受 15% 折扣：门槛判断使用 >800 而非 >=800

- 严重度：主要（major）
- 严重度依据：需求 R3 与示例 E2 明确 800 元应享 15%（120 元）。恰好 800 元的订单优惠被完全抹掉，应付多算 120 元，核心金额规则在等号边界失效；800 是常见整数价位且无任何提示。同类输入 801 元可正常得到 120/681（TC-CART-015 通过），说明门槛被写成严格大于。
- 分类：产品（APP）
- 状态：待处理（open）
- 复现状态：已复现；复现次数：2
- 复现环境：Windows 11 10.0.26340 / Python 3.13.9 / Selenium 4.51.0 / Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / headless 1280x900 / http://127.0.0.1:8765/
- 预期：discount=120；payable=680（R3 silver>=800 -> 15%；E2）
- 实际：discount=0；payable=800；message=(空)
- 说明：TC-CART-002 输入 amount=800、coupon=CP1234、level=silver、points 未勾选，实测 discount=0、payable=800、message 为空。需求 R3 规定银卡订单金额 >=800 时折扣率 15%，优惠 floor(800x0.15)=120，应付 680；第 3 节 E2 给出同样的期望对。独立复现脚本 repro.py 第二次执行得到相同结果。

**前置条件**
1. 页面处于初始状态：amount 与 coupon 为空、level=regular、points 未勾选
2. 测试数据 amount=800、coupon=CP1234、level=silver、points 未勾选

**复现步骤**
1. 打开 http://127.0.0.1:8765/ 并等待「计算」按钮可点击
2. 在 amount 输入 800，在 coupon 输入 CP1234
3. level 选择 silver，points 保持未勾选
4. 点击「计算」按钮
5. 读取 discount 与 payable：实测 0 与 800，期望 120 与 680

## DEF-002 金卡 10% 折扣采用四舍五入而非向下取整：555 元得 56（应 55）

- 严重度：主要（major）
- 严重度依据：R3 明文要求「优惠金额一律向下取整到整元（不得四舍五入）」；555x0.10=55.5 被算成 56，应付 499 而非 500。凡是折扣金额小数部分 >=0.5 的订单都会多减 1 元，属系统性金额偏差，且需求用「一律」「不得」明确禁止该行为。
- 分类：产品（APP）
- 状态：待处理（open）
- 复现状态：已复现；复现次数：2
- 复现环境：Windows 11 10.0.26340 / Python 3.13.9 / Selenium 4.51.0 / Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / headless 1280x900 / http://127.0.0.1:8765/
- 预期：discount=55；payable=500（E3；R3 向下取整）
- 实际：discount=56；payable=499；message=(空)
- 说明：TC-CART-003 输入 amount=555、coupon=CP1234、level=gold、points 未勾选，实测 discount=56、payable=499。需求 R3 与第 3 节 E3 给出 55 与 500。同一根因在 9998 元（TC-CART-011）与 9999 元（TC-CART-012）上再次出现，分别得 1000。独立复现脚本 repro.py 第二次执行结果一致。

**前置条件**
1. 页面处于初始状态：amount 与 coupon 为空、level=regular、points 未勾选
2. 测试数据 amount=555、coupon=CP1234、level=gold、points 未勾选

**复现步骤**
1. 打开 http://127.0.0.1:8765/ 并等待「计算」按钮可点击
2. 在 amount 输入 555，在 coupon 输入 CP1234
3. level 选择 gold，points 保持未勾选
4. 点击「计算」按钮
5. 读取 discount 与 payable：实测 56 与 499，期望 55 与 500

## DEF-003 金卡 9998 元折扣四舍五入为 1000（应 999）

- 严重度：次要（minor）
- 严重度依据：与 TC-CART-003 同一根因（未向下取整），但发生在金额上边界附近，单次金额偏差 1 元，业务影响小于中段金额；单独登记以便边界回归可追溯。
- 分类：产品（APP）
- 状态：待处理（open）
- 复现状态：已复现；复现次数：2
- 复现环境：Windows 11 10.0.26340 / Python 3.13.9 / Selenium 4.51.0 / Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / headless 1280x900 / http://127.0.0.1:8765/
- 预期：discount=999；payable=8999（9998x0.1=999.8 floor）
- 实际：discount=1000；payable=8998；message=(空)
- 说明：TC-CART-011 输入 amount=9998、coupon=CP1234、level=gold、points 未勾选，实测 discount=1000、payable=8998；9998x0.10=999.8 向下取整应为 999，应付 8999。独立复现脚本 repro.py 结果一致。根因同 DEF-002（四舍五入），本条为边界取值上的独立证据。

**前置条件**
1. 页面处于初始状态：amount 与 coupon 为空、level=regular、points 未勾选
2. 测试数据 amount=9998、coupon=CP1234、level=gold、points 未勾选

**复现步骤**
1. 打开 http://127.0.0.1:8765/ 并等待「计算」按钮可点击
2. 在 amount 输入 9998，在 coupon 输入 CP1234
3. level 选择 gold，points 保持未勾选
4. 点击「计算」按钮
5. 读取 discount 与 payable：实测 1000 与 8998，期望 999 与 8999

## DEF-004 金卡 9999 元折扣四舍五入为 1000（应 999）

- 严重度：次要（minor）
- 严重度依据：与 TC-CART-003 同一根因（未向下取整），出现在允许金额的最大值上，单次偏差 1 元；作为上边界回归证据独立登记，便于修复后逐条验证。
- 分类：产品（APP）
- 状态：待处理（open）
- 复现状态：已复现；复现次数：2
- 复现环境：Windows 11 10.0.26340 / Python 3.13.9 / Selenium 4.51.0 / Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / headless 1280x900 / http://127.0.0.1:8765/
- 预期：discount=999；payable=9000（9999x0.1=999.9 floor）
- 实际：discount=1000；payable=8999；message=(空)
- 说明：TC-CART-012 输入 amount=9999、coupon=CP1234、level=gold、points 未勾选，实测 discount=1000、payable=8999；9999x0.10=999.9 向下取整应为 999，应付 9000。探索阶段对同一输入也观察到 1000 与 8999，独立复现脚本 repro.py 第三次结果一致。

**前置条件**
1. 页面处于初始状态：amount 与 coupon 为空、level=regular、points 未勾选
2. 测试数据 amount=9999、coupon=CP1234、level=gold、points 未勾选

**复现步骤**
1. 打开 http://127.0.0.1:8765/ 并等待「计算」按钮可点击
2. 在 amount 输入 9999，在 coupon 输入 CP1234
3. level 选择 gold，points 保持未勾选
4. 点击「计算」按钮
5. 读取 discount 与 payable：实测 1000 与 8999，期望 999 与 9000

## DEF-005 优惠券码大小写校验缺失：cp1234 被接受并完成折扣计算

- 严重度：主要（major）
- 严重度依据：R2 规定券码必须匹配 ^CP[A-Z0-9]{4}$，小写属明文列出的非法字符；实现接受小写变体并照常计算折扣，等于绕过券码校验，影响所有含小写的券码而不只是单个取值，属校验规则缺失。
- 分类：产品（APP）
- 状态：待处理（open）
- 复现状态：已复现；复现次数：2
- 复现环境：Windows 11 10.0.26340 / Python 3.13.9 / Selenium 4.51.0 / Chrome 156.0.8078.74 / ChromeDriver 156.0.8078.80 / headless 1280x900 / http://127.0.0.1:8765/
- 预期：message=优惠券码无效；discount=-；payable=-
- 实际：message=(空)；discount=50；payable=450
- 说明：TC-CART-021 输入 amount=500、coupon=cp1234、level=gold、points 未勾选，实测 message 为空、discount=50、payable=450；需求 R2 要求提示「优惠券码无效」且两项显示 -、不进行计算。探索阶段（O-01）与独立复现脚本 repro.py 均得到相同结果，说明实现对比前统一转成了大写（或使用了大小写不敏感的比较）。

**前置条件**
1. 页面处于初始状态：amount 与 coupon 为空、level=regular、points 未勾选
2. 测试数据 amount=500、coupon=cp1234、level=gold、points 未勾选

**复现步骤**
1. 打开 http://127.0.0.1:8765/ 并等待「计算」按钮可点击
2. 在 amount 输入 500，在 coupon 输入 cp1234（全小写）
3. level 选择 gold，points 保持未勾选
4. 点击「计算」按钮
5. 读取 message、discount 与 payable：实测空、50、450，期望优惠券码无效、-、-

