"""CartCheck acceptance suite (black-box Selenium + pytest).

One test per row of `reports/test-cases/cartcheck-test-cases.csv`.  Every test
declares the case level oracle from the requirement, performs a real
interaction, records the observed values and asserts against the requirement -
never against what the application happened to display during exploration.

Expected values come from `fixtures/cartcheck/REQUIREMENTS.md`:
  * R1 amount 1..9999 integer, otherwise `金额需为 1-9999 的整数` + `-` / `-`
  * R2 coupon `^CP[A-Z0-9]{4}$`, otherwise `优惠券码无效` + `-` / `-`
  * R3 gold >= 500 -> 10% floor, silver >= 800 -> 15% floor, otherwise 0
  * R4 points -> payable = amount - discount - 1, never below 0
  * R5 regular -> discount 0, no error
"""
from __future__ import annotations

import pytest

from page_cartcheck import CartcheckPage, normalise_money

MSG_AMOUNT = "金额需为 1-9999 的整数"
MSG_COUPON = "优惠券码无效"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _calculate(case_ctx, amount: str, coupon: str, level: str, points: bool) -> dict:
    """Drive one calculation on a fresh page and return the observation."""
    page = CartcheckPage(case_ctx.driver)
    load_seconds = page.open()
    case_ctx.step(f"打开 {page.target}，等待「计算」按钮可点击（实测 {load_seconds:.3f}s）")
    case_ctx.step(f"在 amount 输入 {amount!r}，在 coupon 输入 {coupon!r}")
    page.set_amount(amount).set_coupon(coupon)
    case_ctx.step(f"level 选择 {level}，points {'勾选' if points else '不勾选'}")
    page.set_level(level).set_points(points)
    case_ctx.step("点击「计算」按钮")
    page.click_calc()
    ready = page.wait_for_result()
    case_ctx.step(f"等待输出变化完成（触发通道：{ready}）")
    observed = {
        "discount": page.discount_text(),
        "payable": page.payable_text(),
        "message": page.message_text(),
        "channel": ready,
        "load_seconds": load_seconds,
        "scroll": page.scroll_metrics(),
    }
    case_ctx.set_actual(
        f"discount={observed['discount']}；payable={observed['payable']}；"
        f"message={observed['message'] or '(空)'}"
    )
    case_ctx.screenshot("result", element=page.results_container())
    return observed


def _assert_amounts(case_ctx, observed: dict, expected_discount: int, expected_payable: int) -> None:
    raw_discount = observed["discount"]
    raw_payable = observed["payable"]
    try:
        discount = normalise_money(raw_discount)
    except ValueError as exc:
        case_ctx.check(False, "优惠金额为整数文本", expected_discount, f"{raw_discount!r} ({exc})")
        return
    case_ctx.check(discount == expected_discount, "优惠金额", expected_discount, raw_discount)
    try:
        payable = normalise_money(raw_payable)
    except ValueError as exc:
        case_ctx.check(False, "应付金额为整数文本", expected_payable, f"{raw_payable!r} ({exc})")
        return
    case_ctx.check(payable == expected_payable, "应付金额", expected_payable, raw_payable)
    case_ctx.check(
        observed["message"] not in (MSG_AMOUNT, MSG_COUPON),
        "合法输入不应出现错误提示",
        f"message 不属于 ({MSG_AMOUNT} | {MSG_COUPON})",
        observed["message"] or "(空)",
    )


def _assert_error(case_ctx, observed: dict, expected_message: str) -> None:
    case_ctx.check(observed["message"] == expected_message, "提示文案", expected_message,
                   observed["message"] or "(空)")
    case_ctx.check(observed["discount"] == "-", "优惠金额为 -", "-", observed["discount"])
    case_ctx.check(observed["payable"] == "-", "应付金额为 -", "-", observed["payable"])


# --------------------------------------------------------------------------- #
# section 3 examples E1..E7
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-001")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-05")
@pytest.mark.method("判定表+等价类")
@pytest.mark.case_type("positive")
def test_tc_cart_001(case_ctx):
    """E1: 500 / CP1234 / gold / no points -> 50 / 450."""
    case_ctx.set_expected("discount=50；payable=450（需求 E1）")
    observed = _calculate(case_ctx, "500", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 50, 450)


@pytest.mark.case_id("TC-CART-002")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-06")
@pytest.mark.method("判定表+等价类")
@pytest.mark.case_type("positive")
def test_tc_cart_002(case_ctx):
    """E2: 800 / CP1234 / silver / no points -> 120 / 680."""
    case_ctx.set_expected("discount=120；payable=680（需求 E2）")
    observed = _calculate(case_ctx, "800", "CP1234", "silver", False)
    _assert_amounts(case_ctx, observed, 120, 680)


@pytest.mark.case_id("TC-CART-003")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-05")
@pytest.mark.method("边界值+取整口径")
@pytest.mark.case_type("boundary")
def test_tc_cart_003(case_ctx):
    """E3: 555 * 0.10 = 55.5 must floor to 55 (not round to 56)."""
    case_ctx.set_expected("discount=55；payable=500（555x0.1=55.5 floor=55，需求 E3 + R3 取整）")
    observed = _calculate(case_ctx, "555", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 55, 500)


@pytest.mark.case_id("TC-CART-004")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-08")
@pytest.mark.method("判定表")
@pytest.mark.case_type("positive")
def test_tc_cart_004(case_ctx):
    """E4: 500 / gold / points -> 50 / 449."""
    case_ctx.set_expected("discount=50；payable=449（需求 E4）")
    observed = _calculate(case_ctx, "500", "CP1234", "gold", True)
    _assert_amounts(case_ctx, observed, 50, 449)


@pytest.mark.case_id("TC-CART-005")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-07")
@pytest.mark.method("判定表")
@pytest.mark.case_type("positive")
def test_tc_cart_005(case_ctx):
    """E5: 1000 / regular -> 0 / 1000."""
    case_ctx.set_expected("discount=0；payable=1000（需求 E5）")
    observed = _calculate(case_ctx, "1000", "CP1234", "regular", False)
    _assert_amounts(case_ctx, observed, 0, 1000)


@pytest.mark.case_id("TC-CART-006")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-07;REQ-11")
@pytest.mark.method("边界值 3-value（499/500/501）")
@pytest.mark.case_type("boundary")
def test_tc_cart_006(case_ctx):
    """E6: 499 / gold -> 0 / 499 (below the 500 threshold)."""
    case_ctx.set_expected("discount=0；payable=499（需求 E6）")
    observed = _calculate(case_ctx, "499", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 0, 499)


@pytest.mark.case_id("TC-CART-007")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-10;REQ-07;REQ-11")
@pytest.mark.method("边界值 3-value（799/800/801）")
@pytest.mark.case_type("boundary")
def test_tc_cart_007(case_ctx):
    """E7: 799 / silver -> 0 / 799 (below the 800 threshold)."""
    case_ctx.set_expected("discount=0；payable=799（需求 E7）")
    observed = _calculate(case_ctx, "799", "CP1234", "silver", False)
    _assert_amounts(case_ctx, observed, 0, 799)


# --------------------------------------------------------------------------- #
# amount boundaries
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-008")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-02;REQ-11")
@pytest.mark.method("边界值 3-value（0/1/2）+ 无效分区")
@pytest.mark.case_type("boundary")
def test_tc_cart_008(case_ctx):
    """Amount 0 is below the lower boundary -> error, no amounts."""
    case_ctx.set_expected(f"message={MSG_AMOUNT}；discount=-；payable=-")
    observed = _calculate(case_ctx, "0", "CP1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_AMOUNT)


@pytest.mark.case_id("TC-CART-009")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-01;REQ-11")
@pytest.mark.method("边界值 3-value（0/1/2）")
@pytest.mark.case_type("boundary")
def test_tc_cart_009(case_ctx):
    """Amount 1 is the smallest valid integer -> 0 / 1."""
    case_ctx.set_expected("discount=0；payable=1")
    observed = _calculate(case_ctx, "1", "CP1234", "regular", False)
    _assert_amounts(case_ctx, observed, 0, 1)


@pytest.mark.case_id("TC-CART-010")
@pytest.mark.priority("P2")
@pytest.mark.requirement("REQ-01;REQ-11")
@pytest.mark.method("边界值 3-value（0/1/2）")
@pytest.mark.case_type("boundary")
def test_tc_cart_010(case_ctx):
    """Amount 2 is the adjacent valid value -> 0 / 2."""
    case_ctx.set_expected("discount=0；payable=2")
    observed = _calculate(case_ctx, "2", "CP1234", "regular", False)
    _assert_amounts(case_ctx, observed, 0, 2)


@pytest.mark.case_id("TC-CART-011")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-01;REQ-05;REQ-11")
@pytest.mark.method("边界值 3-value（9998/9999/10000）")
@pytest.mark.case_type("boundary")
def test_tc_cart_011(case_ctx):
    """9998 * 0.10 = 999.8 must floor to 999 -> payable 8999."""
    case_ctx.set_expected("discount=999；payable=8999（9998x0.1=999.8 floor=999）")
    observed = _calculate(case_ctx, "9998", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 999, 8999)


@pytest.mark.case_id("TC-CART-012")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-01;REQ-05;REQ-11")
@pytest.mark.method("边界值 3-value（9998/9999/10000）")
@pytest.mark.case_type("boundary")
def test_tc_cart_012(case_ctx):
    """9999 * 0.10 = 999.9 must floor to 999 -> payable 9000."""
    case_ctx.set_expected("discount=999；payable=9000（9999x0.1=999.9 floor=999）")
    observed = _calculate(case_ctx, "9999", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 999, 9000)


@pytest.mark.case_id("TC-CART-013")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-02;REQ-11")
@pytest.mark.method("边界值 3-value（9998/9999/10000）+ 无效分区")
@pytest.mark.case_type("boundary")
def test_tc_cart_013(case_ctx):
    """10000 is above the upper boundary -> error, no amounts."""
    case_ctx.set_expected(f"message={MSG_AMOUNT}；discount=-；payable=-")
    observed = _calculate(case_ctx, "10000", "CP1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_AMOUNT)


@pytest.mark.case_id("TC-CART-014")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-05;REQ-11")
@pytest.mark.method("边界值 3-value（499/500/501）")
@pytest.mark.case_type("boundary")
def test_tc_cart_014(case_ctx):
    """501 * 0.10 = 50.1 must floor to 50 -> payable 451."""
    case_ctx.set_expected("discount=50；payable=451")
    observed = _calculate(case_ctx, "501", "CP1234", "gold", False)
    _assert_amounts(case_ctx, observed, 50, 451)


@pytest.mark.case_id("TC-CART-015")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-06;REQ-11")
@pytest.mark.method("边界值 3-value（799/800/801）")
@pytest.mark.case_type("boundary")
def test_tc_cart_015(case_ctx):
    """801 * 0.15 = 120.15 must floor to 120 -> payable 681."""
    case_ctx.set_expected("discount=120；payable=681")
    observed = _calculate(case_ctx, "801", "CP1234", "silver", False)
    _assert_amounts(case_ctx, observed, 120, 681)


# --------------------------------------------------------------------------- #
# amount invalid partitions
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-016")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-02")
@pytest.mark.method("等价类（空值无效分区）")
@pytest.mark.case_type("negative")
def test_tc_cart_016(case_ctx):
    """Empty amount -> error message, no calculation."""
    case_ctx.set_expected(f"message={MSG_AMOUNT}；discount=-；payable=-")
    observed = _calculate(case_ctx, "", "CP1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_AMOUNT)


@pytest.mark.case_id("TC-CART-017")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-02")
@pytest.mark.method("等价类（非整数无效分区）")
@pytest.mark.case_type("negative")
def test_tc_cart_017(case_ctx):
    """Decimal amount 500.5 is not an integer -> error message."""
    case_ctx.set_expected(f"message={MSG_AMOUNT}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500.5", "CP1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_AMOUNT)


@pytest.mark.case_id("TC-CART-018")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-02")
@pytest.mark.method("等价类（非数字无效分区）")
@pytest.mark.case_type("negative")
def test_tc_cart_018(case_ctx):
    """Non-numeric amount abc -> error message."""
    case_ctx.set_expected(f"message={MSG_AMOUNT}；discount=-；payable=-")
    observed = _calculate(case_ctx, "abc", "CP1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_AMOUNT)


# --------------------------------------------------------------------------- #
# coupon negatives
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-019")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-04;REQ-11")
@pytest.mark.method("格式边界（长度 5/6/7）")
@pytest.mark.case_type("negative")
def test_tc_cart_019(case_ctx):
    """Coupon CP123 (5 chars) is too short -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "CP123", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-020")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-04;REQ-11")
@pytest.mark.method("格式边界（长度 5/6/7）")
@pytest.mark.case_type("negative")
def test_tc_cart_020(case_ctx):
    """Coupon CP12345 (7 chars) is too long -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "CP12345", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-021")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-04;REQ-11")
@pytest.mark.method("格式错误猜测（字符集）")
@pytest.mark.case_type("negative")
def test_tc_cart_021(case_ctx):
    """Lowercase coupon cp1234 violates ^CP[A-Z0-9]{4}$ -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "cp1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-022")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-04;REQ-11")
@pytest.mark.method("格式错误猜测（字符集）")
@pytest.mark.case_type("negative")
def test_tc_cart_022(case_ctx):
    """Coupon CP12!4 contains a symbol -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "CP12!4", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-023")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-04;REQ-11")
@pytest.mark.method("格式错误猜测（字符集）")
@pytest.mark.case_type("negative")
def test_tc_cart_023(case_ctx):
    """Coupon 'CP 234' contains a space -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "CP 234", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-024")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-04")
@pytest.mark.method("格式错误猜测（前缀）")
@pytest.mark.case_type("negative")
def test_tc_cart_024(case_ctx):
    """Coupon XX1234 has the wrong prefix -> coupon error."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "500", "XX1234", "gold", False)
    _assert_error(case_ctx, observed, MSG_COUPON)


@pytest.mark.case_id("TC-CART-025")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-04")
@pytest.mark.method("判定表（规则列 9：C2=否 且 C5=是）")
@pytest.mark.case_type("combination")
def test_tc_cart_025(case_ctx):
    """Invalid coupon wins over the gold discount and the points flag."""
    case_ctx.set_expected(f"message={MSG_COUPON}；discount=-；payable=-")
    observed = _calculate(case_ctx, "600", "CP12", "gold", True)
    _assert_error(case_ctx, observed, MSG_COUPON)


# --------------------------------------------------------------------------- #
# points
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-026")
@pytest.mark.priority("P0")
@pytest.mark.requirement("REQ-08")
@pytest.mark.method("输出边界值（0/1）+ 判定表")
@pytest.mark.case_type("boundary")
def test_tc_cart_026(case_ctx):
    """Amount 1 with points: payable must clamp at 0, never negative."""
    case_ctx.set_expected("discount=0；payable=0")
    observed = _calculate(case_ctx, "1", "CP1234", "regular", True)
    _assert_amounts(case_ctx, observed, 0, 0)
    case_ctx.check(not observed["payable"].startswith("-"), "应付金额非负", ">=0", observed["payable"])


@pytest.mark.case_id("TC-CART-027")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-08;REQ-09")
@pytest.mark.method("判定表（规则列 8）")
@pytest.mark.case_type("positive")
def test_tc_cart_027(case_ctx):
    """Regular member 1000 with points -> 0 / 999 and no error."""
    case_ctx.set_expected("discount=0；payable=999")
    observed = _calculate(case_ctx, "1000", "CP1234", "regular", True)
    _assert_amounts(case_ctx, observed, 0, 999)
    case_ctx.check(observed["message"] not in (MSG_AMOUNT, MSG_COUPON),
                   "普通会员不因无折扣报错", "无错误提示", observed["message"] or "(空)")


@pytest.mark.case_id("TC-CART-028")
@pytest.mark.priority("P2")
@pytest.mark.requirement("REQ-07;REQ-08")
@pytest.mark.method("判定表（规则列 6 + 7）")
@pytest.mark.case_type("combination")
def test_tc_cart_028(case_ctx):
    """Silver 799 below threshold plus points -> 0 / 798."""
    case_ctx.set_expected("discount=0；payable=798")
    observed = _calculate(case_ctx, "799", "CP1234", "silver", True)
    _assert_amounts(case_ctx, observed, 0, 798)


# --------------------------------------------------------------------------- #
# coupon charset (legal)
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-029")
@pytest.mark.priority("P2")
@pytest.mark.requirement("REQ-03;REQ-11")
@pytest.mark.method("格式等价类（大写字母类）")
@pytest.mark.case_type("positive")
def test_tc_cart_029(case_ctx):
    """Coupon CPABCD (4 uppercase letters) is legal -> 50 / 450."""
    case_ctx.set_expected("discount=50；payable=450（券码视为合法，无券码错误提示）")
    observed = _calculate(case_ctx, "500", "CPABCD", "gold", False)
    _assert_amounts(case_ctx, observed, 50, 450)


# --------------------------------------------------------------------------- #
# non functional
# --------------------------------------------------------------------------- #
@pytest.mark.case_id("TC-CART-030")
@pytest.mark.priority("P1")
@pytest.mark.requirement("REQ-12;REQ-13")
@pytest.mark.method("非功能阈值检查（MS-07）")
@pytest.mark.case_type("nonfunctional")
def test_tc_cart_030(case_ctx):
    """Viewport layout, result visibility, no dialog, 2s interactivity."""
    case_ctx.set_expected("scrollWidth<=clientWidth；discount/payable/message 计算前后均可见；"
                          "alert 计数=0；load_to_clickable<=2.0s")
    page = CartcheckPage(case_ctx.driver)
    load_seconds = page.open()
    case_ctx.step(f"1280x900 视口打开页面，计时到「计算」按钮可点击：{load_seconds:.3f}s")
    before = page.outputs_displayed()
    metrics = page.scroll_metrics()
    case_ctx.step(
        "读取布局：scrollWidth={scrollWidth} clientWidth={clientWidth} innerWidth={innerWidth}".format(**metrics)
    )
    page.set_amount("500").set_coupon("CP1234").set_level("gold").set_points(False)
    page.click_calc()
    channel = page.wait_for_result()
    after = page.outputs_displayed()
    alerts = page.alert_count()
    native = page.native_alert()
    case_ctx.step(f"计算完成（{channel}），再次读取输出可见性，alert 计数={alerts}，原生对话框={native}")
    case_ctx.set_actual(
        f"scrollWidth={metrics['scrollWidth']}；clientWidth={metrics['clientWidth']}；"
        f"before={before}；after={after}；alert_count={alerts}；"
        f"native_alert={native['present']}；load_to_clickable={load_seconds:.3f}s"
    )
    case_ctx.screenshot("layout", full_page=True)
    case_ctx.check(metrics["scrollWidth"] <= metrics["clientWidth"], "无横向滚动",
                   f"scrollWidth<=clientWidth ({metrics['clientWidth']})", metrics["scrollWidth"])
    case_ctx.check(all(before.values()), "计算前结果区可见", True, before)
    case_ctx.check(all(after.values()), "计算后结果区可见", True, after)
    case_ctx.check(alerts == 0 and not native["present"], "无 JavaScript 弹窗", 0,
                   alerts if not native["present"] else f"{alerts} + native:{native['text']}")
    case_ctx.check(load_seconds <= 2.0, "2 秒内可交互", "<=2.0s", f"{load_seconds:.3f}s")
