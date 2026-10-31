# CartCheck 浏览器探索报告（只读）

- 运行 ID：`RUN-20261031-COLDSTART-01`
- 目标：`http://127.0.0.1:8765/`
- 探索方式：Selenium（headless Chrome 156.0.8078.74 + ChromeDriver 156.0.8078.80），
  脚本 `pipeline_runs/RUN-20261031-COLDSTART-01/explore.py`，原始记录 `exploration.json`
- 探索时间：2026-10-31T01:00:04+08:00
- 边界说明：未读取 `fixtures/cartcheck/app.js` / `index.html` / `styles.css` / `serve.py`；
  全部选择器来自真实 DOM 读取结果。

## 1. 页面基本信息

| 项 | 实测值 |
|---|---|
| `document.title` | `CartCheck 结算试算器` |
| URL | `http://127.0.0.1:8765/` |
| 窗口大小 | 1280 × 900（`--window-size=1280,900`, device scale factor 1） |
| 视口 | innerWidth 1254 / innerHeight 744 / dpr 1 |
| 滚动尺寸 | scrollWidth 1254 = clientWidth 1254（无横向滚动）；scrollHeight 744 |
| 首次可交互 | `driver.get()` 返回到「计算」按钮 `element_to_be_clickable` = **0.21 s** |
| 页面语言 | 未设置 `lang` 属性（`document.documentElement.lang` 为空字符串） |

## 2. `data-testid` 元素清单（真实 DOM，8/8 命中）

| data-testid | tag | type | id/name | 可见 | 尺寸(w×h) | 初始文本/值 | 备注 |
|---|---|---|---|---|---|---|---|
| `amount` | input | text | id=amount, name=amount | 是 | 518×42 | `""` | 可编辑 |
| `coupon` | input | text | id=coupon, name=coupon | 是 | 518×42 | `""` | 可编辑 |
| `level` | select | - | id=level, name=level | 是 | 518×42 | `regular` | 选项：`regular`（默认选中）/`silver`/`gold`，文案分别为「普通会员 regular」「银卡 silver」「金卡 gold」 |
| `points` | input | checkbox | id=points, name=points | 是 | 18×18 | `false` | 未选中 |
| `calc` | button | button | id=calc | 是 | 132×44 | 文本「计算」 | 可点击 |
| `discount` | **output** | - | 无 id | 是 | 初始 12×40 | `-` | 计算后文本为纯整数（如 `50`），字体 30px/700 |
| `payable` | **output** | - | 无 id | 是 | 初始 12×40 | `-` | 同上 |
| `message` | p | - | class=message, **role=status** | 是 | 710×24 | `""`（空） | 14px，颜色 `rgb(180,35,24)`；空字符串时仍占位可见 |

关键发现：
- `discount` / `payable` 是 `<output>` 元素，`.text` 与 JS `textContent` 一致，无千分位、无货币符号、无小数（实测 `50`、`999`、`1000`）。
- `message` 在成功计算时保持**空字符串**（需求未规定成功文案，见缺口 G-01）。
- 三个输出元素在计算前均 `displayed=true`（`offsetWidth/Height` 非零），满足「计算前后都可见」的观察前提。

## 3. 稳定选择器（后续 Page Object 只使用这些）

```text
input[data-testid="amount"]
input[data-testid="coupon"]
select[data-testid="level"]           # 取值 regular / silver / gold
input[data-testid="points"]
button[data-testid="calc"]
[data-testid="discount"]              # output
[data-testid="payable"]               # output
[data-testid="message"]               # p[role=status]
```

未使用任何 CSS class 或位置选择器（`message` 的 class 仅作为探索记录）。

## 4. 交互路径（全部真实点击，未修改页面）

| # | 动作 | 观察 |
|---|---|---|
| 1 | 打开页面 | 输出 `-` / `-`，message 空，level=regular，points 未勾选 |
| 2 | 500 / CP1234 / gold / 未勾选积分 → 计算 | discount `50`，payable `450`（与 E1 一致） |
| 3 | 金额改为 0 → 计算 | message `金额需为 1-9999 的整数`，discount `-`，payable `-` |
| 4 | 金额 500 / 券码 `cp1234` / gold → 计算 | message 空，discount `50`，payable `450`（**小写券码未按 R2 拒绝**，见 §6 观察 O-01） |
| 5 | 555 / CP1234 / gold → 计算 | discount `56`，payable `499`（**需求 E3 为 55 / 500**，见 O-02） |
| 6 | 同上 + 勾选叠加积分 → 计算 | discount `56`，payable `498`（即 -1 生效） |
| 7 | 800 / CP1234 / silver → 计算 | discount `0`，payable `800`（**需求 E2 为 120 / 680**，见 O-03） |
| 8 | 9999 / CP1234 / gold → 计算 | discount `1000`，payable `8999`（**需求要求 floor(999.9)=999 → 9000**，见 O-02） |

每次点击后输出变化均在 3 s 显式等待内被观察到（实测状态切换远快于该阈值），未使用固定 sleep。

## 5. 控制台与弹窗

- 浏览器控制台（`driver.get_log("browser")`，level ALL）：**0 条**记录，`console_errors` 为空数组。
  原始日志：`evidence/logs/RUN-20261031-COLDSTART-01/EXPLORE__browser__20261030T170006-425.log`（EV-231a844f7d）。
- 探索全程未出现 `alert`/`confirm`/`prompt`（Selenium 未抛 `UnexpectedAlertPresentException`）。
- 未发现资源 404 或脚本报错。

## 6. 探索观察（观察 ≠ 缺陷，须由正式用例确认）

| 编号 | 观察 | 需求依据 | 后续动作 |
|---|---|---|---|
| O-01 | 券码 `cp1234`（含小写）被接受并产生 50/450，message 为空 | R2 要求 `^CP[A-Z0-9]{4}$`，含小写属非法 → 应提示「优惠券码无效」且两项为 `-` | 设计负向用例 TC-CART-021 确认 |
| O-02 | 555×10% 得 `56`，9999×10% 得 `1000`，表现为四舍五入而非 floor | R3「优惠金额一律向下取整到整元（不得四舍五入）」 | 设计 TC-CART-003、TC-CART-012 确认 |
| O-03 | 800 银卡得 0 折扣 | R3「银卡 ≥800 → 15%」，E2 期望 120/680 | 设计 TC-CART-002（及 801 邻近值 TC-CART-015）确认 |
| O-04 | 成功计算时 message 为空 | 需求未规定成功文案（缺口 G-01） | 成功用例不断言 message 文本 |
| O-05 | 输出为纯整数文本，无千分位 | 未规定格式（缺口 G-03） | 断言按整数比较文本 |

> 以上 O-01..O-03 只是探索期的单次观察，不作为缺陷结论；是否登记缺陷由正式用例执行结果决定。

## 7. 未覆盖 / 未探索的路径

- 浏览器前进/后退、刷新持久化：需求第 6 节明确「无持久化，刷新后清空属预期」，不在范围。
- 键盘回车提交：需求只规定「点击计算」，未探索回车行为（不生成用例，避免编造规则）。
- 移动端/响应式断点、其它浏览器：需求第 6 节明确非目标。
- 金额前导零、`+500`、前后空格：需求未定义（缺口 G-02），不生成正式用例。

## 8. 证据登记

| 证据 ID | 类型 | 路径 | 说明 |
|---|---|---|---|
| EV-851b174e12 | screenshot | `evidence/raw/RUN-20261031-COLDSTART-01/EXPLORE/EXPLORE__initial__viewport__20261030T170004-883.png` | 初始状态整屏（1254×744） |
| EV-bc836119bd | element-screenshot | `evidence/raw/RUN-20261031-COLDSTART-01/EXPLORE/EXPLORE__e1-result__element__20261030T170005-325.png` | E1 计算后关键区域（表单+结果区，760×744） |
| EV-231a844f7d | log | `evidence/logs/RUN-20261031-COLDSTART-01/EXPLORE__browser__20261030T170006-425.log` | 浏览器控制台（空） |

## 9. 对测试设计的影响

1. 所有定位使用上表 8 个 `data-testid`，不使用文本定位（按钮文案「计算」可用于辅助断言但不作为主定位）。
2. 输出断言比较**文本标准化后的整数**（去空白），因为需求未规定格式，但值必须可精确比较。
3. 成功路径不产生 message 文本，因此成功用例只断言 discount/payable；错误路径同时断言 message 文案与两项 `-`。
4. 探索已暴露 3 个疑似规则偏差（O-01..O-03），正式用例按需求预期设计，不使用探索观察值作为预期。
