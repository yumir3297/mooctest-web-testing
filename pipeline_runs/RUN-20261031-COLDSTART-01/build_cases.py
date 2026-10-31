"""Build the CartCheck case table (CSV + machine readable JSON) from one source.

Design follows test-design-methodology: MS-01 (partitions + 3-value BVA),
MS-02 (format/enum), MS-03 (decision table), MS-09 (stop when coverage items
are hit), ORA-01/02/03 (expected from spec/derivation), REV-02/03/08.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "RUN-20261031-COLDSTART-01"
OUT_CSV = ROOT / "reports" / "test-cases" / "cartcheck-test-cases.csv"
OUT_JSON = ROOT / "pipeline_runs" / RUN / "cases.json"
AUT = "tests/generated/cartcheck/test_cartcheck.py::{}"

PRE = "页面已打开 http://127.0.0.1:8765/，表单为初始状态（amount 与 coupon 为空，level=regular，points 未勾选）"

MSG_AMT = "金额需为 1-9999 的整数"
MSG_CPN = "优惠券码无效"
ERR_AMT = f"message={MSG_AMT}；discount=-；payable=-"
ERR_CPN = f"message={MSG_CPN}；discount=-；payable=-"

ROWS = [
    # --- section 3 examples -------------------------------------------------
    dict(case_id="TC-CART-001", title="金卡满 500 享 10% 折扣：E1 应得优惠 50、应付 450",
         priority="P0", requirement_ids="REQ-10;REQ-05", case_type="positive",
         method="判定表+等价类", test_data="amount=500；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 保持 points 未勾选 5. 点击计算",
         expected="discount=50；payable=450（需求 E1）",
         notes="ORACLE-SPEC（REQUIREMENTS.md 第 3 节 E1）"),
    dict(case_id="TC-CART-002", title="银卡满 800 享 15% 折扣：E2 应得优惠 120、应付 680",
         priority="P0", requirement_ids="REQ-10;REQ-06", case_type="positive",
         method="判定表+等价类", test_data="amount=800；coupon=CP1234；level=silver；points=未勾选",
         steps="1. 在 amount 输入 800 2. 在 coupon 输入 CP1234 3. level 选择 silver 4. 保持 points 未勾选 5. 点击计算",
         expected="discount=120；payable=680（需求 E2）",
         notes="ORACLE-SPEC（REQUIREMENTS.md 第 3 节 E2）"),
    dict(case_id="TC-CART-003", title="金卡 555 元的 10% 折扣必须向下取整：55 而非 56",
         priority="P0", requirement_ids="REQ-10;REQ-05", case_type="boundary",
         method="边界值+取整口径", test_data="amount=555；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 555 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected="discount=55；payable=500（555x0.1=55.5 floor=55，需求 E3 + R3 取整）",
         notes="ORACLE-SPEC（E3）+ R3「向下取整到整元（不得四舍五入）」；四舍五入实现会得 56/499"),
    dict(case_id="TC-CART-004", title="金卡 500 元叠加积分：折后应付再减 1 元等于 449",
         priority="P0", requirement_ids="REQ-10;REQ-08", case_type="positive",
         method="判定表", test_data="amount=500；coupon=CP1234；level=gold；points=勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 勾选 points 5. 点击计算",
         expected="discount=50；payable=449（需求 E4）",
         notes="ORACLE-SPEC（REQUIREMENTS.md 第 3 节 E4）"),
    dict(case_id="TC-CART-005", title="普通会员 1000 元无折扣：优惠 0、应付等于订单金额",
         priority="P0", requirement_ids="REQ-10;REQ-07", case_type="positive",
         method="判定表", test_data="amount=1000；coupon=CP1234；level=regular；points=未勾选",
         steps="1. 在 amount 输入 1000 2. 在 coupon 输入 CP1234 3. level 选择 regular 4. 点击计算",
         expected="discount=0；payable=1000（需求 E5）",
         notes="ORACLE-SPEC（REQUIREMENTS.md 第 3 节 E5）"),
    dict(case_id="TC-CART-006", title="金卡 499 元未达门槛：优惠 0、应付 499",
         priority="P0", requirement_ids="REQ-10;REQ-07;REQ-11", case_type="boundary",
         method="边界值 3-value（499/500/501）", test_data="amount=499；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 499 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected="discount=0；payable=499（需求 E6）",
         notes="ORACLE-SPEC（E6）；金卡门槛下侧邻近值"),
    dict(case_id="TC-CART-007", title="银卡 799 元未达门槛：优惠 0、应付 799",
         priority="P0", requirement_ids="REQ-10;REQ-07;REQ-11", case_type="boundary",
         method="边界值 3-value（799/800/801）", test_data="amount=799；coupon=CP1234；level=silver；points=未勾选",
         steps="1. 在 amount 输入 799 2. 在 coupon 输入 CP1234 3. level 选择 silver 4. 点击计算",
         expected="discount=0；payable=799（需求 E7）",
         notes="ORACLE-SPEC（E7）；银卡门槛下侧邻近值"),
    # --- amount boundaries --------------------------------------------------
    dict(case_id="TC-CART-008", title="金额 0 低于下边界：提示金额错误且两项输出为 -",
         priority="P0", requirement_ids="REQ-02;REQ-11", case_type="boundary",
         method="边界值 3-value（0/1/2）+ 无效分区", test_data="amount=0；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 0 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_AMT,
         notes="ORACLE-SPEC（R1 第 29 行文案）；金额下边界外侧值"),
    dict(case_id="TC-CART-009", title="金额 1 为最小有效值：普通会员优惠 0、应付 1",
         priority="P1", requirement_ids="REQ-01;REQ-11", case_type="boundary",
         method="边界值 3-value（0/1/2）", test_data="amount=1；coupon=CP1234；level=regular；points=未勾选",
         steps="1. 在 amount 输入 1 2. 在 coupon 输入 CP1234 3. level 选择 regular 4. 点击计算",
         expected="discount=0；payable=1",
         notes="ORACLE-DERIVED（R1 有效端点 + R3 regular 0 折扣）；金额下边界"),
    dict(case_id="TC-CART-010", title="金额 2 为下边界邻近有效值：普通会员应付 2",
         priority="P2", requirement_ids="REQ-01;REQ-11", case_type="boundary",
         method="边界值 3-value（0/1/2）", test_data="amount=2；coupon=CP1234；level=regular；points=未勾选",
         steps="1. 在 amount 输入 2 2. 在 coupon 输入 CP1234 3. level 选择 regular 4. 点击计算",
         expected="discount=0；payable=2",
         notes="ORACLE-DERIVED（R1 有效分区 + R3 regular）；与 TC-CART-009 覆盖项不同（边界邻近值）"),
    dict(case_id="TC-CART-011", title="金额 9998 为有效上边界邻近值：金卡优惠 999、应付 8999",
         priority="P1", requirement_ids="REQ-01;REQ-05;REQ-11", case_type="boundary",
         method="边界值 3-value（9998/9999/10000）", test_data="amount=9998；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 9998 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected="discount=999；payable=8999（9998x0.1=999.8 floor=999）",
         notes="ORACLE-DERIVED（R3 10% + floor）；四舍五入实现会得 1000/8998"),
    dict(case_id="TC-CART-012", title="金额 9999 为有效上边界：金卡优惠 999、应付 9000",
         priority="P1", requirement_ids="REQ-01;REQ-05;REQ-11", case_type="boundary",
         method="边界值 3-value（9998/9999/10000）", test_data="amount=9999；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 9999 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected="discount=999；payable=9000（9999x0.1=999.9 floor=999）",
         notes="ORACLE-DERIVED（R3 10% + floor）；四舍五入实现会得 1000/8999"),
    dict(case_id="TC-CART-013", title="金额 10000 超出上边界：提示金额错误且两项输出为 -",
         priority="P0", requirement_ids="REQ-02;REQ-11", case_type="boundary",
         method="边界值 3-value（9998/9999/10000）+ 无效分区", test_data="amount=10000；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 10000 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_AMT,
         notes="ORACLE-SPEC（R1 第 29 行文案）；金额上边界外侧值"),
    # --- threshold neighbours ----------------------------------------------
    dict(case_id="TC-CART-014", title="金卡 501 元刚过门槛：优惠 floor(50.1)=50、应付 451",
         priority="P1", requirement_ids="REQ-05;REQ-11", case_type="boundary",
         method="边界值 3-value（499/500/501）", test_data="amount=501；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 501 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected="discount=50；payable=451",
         notes="ORACLE-DERIVED（R3 10% + floor）；金卡门槛上侧邻近值"),
    dict(case_id="TC-CART-015", title="银卡 801 元刚过门槛：优惠 floor(120.15)=120、应付 681",
         priority="P1", requirement_ids="REQ-06;REQ-11", case_type="boundary",
         method="边界值 3-value（799/800/801）", test_data="amount=801；coupon=CP1234；level=silver；points=未勾选",
         steps="1. 在 amount 输入 801 2. 在 coupon 输入 CP1234 3. level 选择 silver 4. 点击计算",
         expected="discount=120；payable=681",
         notes="ORACLE-DERIVED（R3 15% + floor）；银卡门槛上侧邻近值"),
    # --- amount invalid partitions -----------------------------------------
    dict(case_id="TC-CART-016", title="金额为空：提示金额错误且不进行计算",
         priority="P0", requirement_ids="REQ-02", case_type="negative",
         method="等价类（空值无效分区）", test_data="amount=（空）；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 保持 amount 为空 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_AMT,
         notes="ORACLE-SPEC（R1「空值」）"),
    dict(case_id="TC-CART-017", title="金额为小数 500.5：属于非整数，必须拒绝",
         priority="P0", requirement_ids="REQ-02", case_type="negative",
         method="等价类（非整数无效分区）", test_data="amount=500.5；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500.5 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_AMT,
         notes="ORACLE-SPEC（R1「非整数（含小数）」）"),
    dict(case_id="TC-CART-018", title="金额为非数字 abc：提示金额错误且两项输出为 -",
         priority="P1", requirement_ids="REQ-02", case_type="negative",
         method="等价类（非数字无效分区）", test_data="amount=abc；coupon=CP1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 abc 2. 在 coupon 输入 CP1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_AMT,
         notes="ORACLE-SPEC（R1「非整数」）；需求未单列字母，按「非整数」归类"),
    # --- coupon negatives ---------------------------------------------------
    dict(case_id="TC-CART-019", title="券码 5 位 CP123：长度不足应提示券码无效",
         priority="P1", requirement_ids="REQ-04;REQ-11", case_type="negative",
         method="格式边界（长度 5/6/7）", test_data="amount=500；coupon=CP123；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP123 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2 长度 6 + 第 4 节长度 5）"),
    dict(case_id="TC-CART-020", title="券码 7 位 CP12345：长度超出应提示券码无效",
         priority="P1", requirement_ids="REQ-04;REQ-11", case_type="negative",
         method="格式边界（长度 5/6/7）", test_data="amount=500；coupon=CP12345；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP12345 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2 长度 6 + 第 4 节长度 7）"),
    dict(case_id="TC-CART-021", title="券码含小写 cp1234：字符集不符必须拒绝",
         priority="P0", requirement_ids="REQ-04;REQ-11", case_type="negative",
         method="格式错误猜测（字符集）", test_data="amount=500；coupon=cp1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 cp1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2 ^CP[A-Z0-9]{4}$ + 第 4 节「小写字母」）；探索观察 O-01 曾出现被接受"),
    dict(case_id="TC-CART-022", title="券码含符号 CP12!4：符号属于非法字符应拒绝",
         priority="P1", requirement_ids="REQ-04;REQ-11", case_type="negative",
         method="格式错误猜测（字符集）", test_data="amount=500；coupon=CP12!4；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP12!4 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2「含空格或符号」+ 第 4 节「符号」）"),
    dict(case_id="TC-CART-023", title="券码含空格 CP 234：空格属于非法字符应拒绝",
         priority="P1", requirement_ids="REQ-04;REQ-11", case_type="negative",
         method="格式错误猜测（字符集）", test_data="amount=500；coupon=CP 234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CP 234 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2「含空格」+ 第 4 节「空格」）；长度为 6 但含空格"),
    dict(case_id="TC-CART-024", title="券码前缀错误 XX1234：前缀不是 CP 应拒绝",
         priority="P1", requirement_ids="REQ-04", case_type="negative",
         method="格式错误猜测（前缀）", test_data="amount=500；coupon=XX1234；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 XX1234 3. level 选择 gold 4. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2「前缀不符」）"),
    dict(case_id="TC-CART-025", title="券码 4 位 CP12 与金卡折扣同时存在：券码校验优先，不得产生金额",
         priority="P0", requirement_ids="REQ-04", case_type="combination",
         method="判定表（规则列 9：C2=否 且 C5=是）", test_data="amount=600；coupon=CP12；level=gold；points=勾选",
         steps="1. 在 amount 输入 600 2. 在 coupon 输入 CP12 3. level 选择 gold 4. 勾选 points 5. 点击计算",
         expected=ERR_CPN,
         notes="ORACLE-SPEC（R2「券码校验先于折扣计算：券码无效时不产生任何金额结果」）"),
    # --- points -------------------------------------------------------------
    dict(case_id="TC-CART-026", title="金额 1 元叠加积分：应付不得为负，最小为 0",
         priority="P0", requirement_ids="REQ-08", case_type="boundary",
         method="输出边界值（0/1）+ 判定表", test_data="amount=1；coupon=CP1234；level=regular；points=勾选",
         steps="1. 在 amount 输入 1 2. 在 coupon 输入 CP1234 3. level 选择 regular 4. 勾选 points 5. 点击计算",
         expected="discount=0；payable=0",
         notes="ORACLE-DERIVED（R4：1-0-1=0 且「不得为负数，最小为 0」）"),
    dict(case_id="TC-CART-027", title="普通会员 1000 元叠加积分：应付为 999 且不报错",
         priority="P1", requirement_ids="REQ-08;REQ-09", case_type="positive",
         method="判定表（规则列 8）", test_data="amount=1000；coupon=CP1234；level=regular；points=勾选",
         steps="1. 在 amount 输入 1000 2. 在 coupon 输入 CP1234 3. level 选择 regular 4. 勾选 points 5. 点击计算",
         expected="discount=0；payable=999",
         notes="ORACLE-DERIVED（R4 + R5）；同时验证 message 不出现两种错误文案"),
    dict(case_id="TC-CART-028", title="银卡 799 元未达门槛并叠加积分：优惠 0、应付 798",
         priority="P2", requirement_ids="REQ-07;REQ-08", case_type="combination",
         method="判定表（规则列 6 + 7）", test_data="amount=799；coupon=CP1234；level=silver；points=勾选",
         steps="1. 在 amount 输入 799 2. 在 coupon 输入 CP1234 3. level 选择 silver 4. 勾选 points 5. 点击计算",
         expected="discount=0；payable=798",
         notes="ORACLE-DERIVED（799<800 无折扣 + R4 减 1）"),
    # --- coupon charset legal ----------------------------------------------
    dict(case_id="TC-CART-029", title="券码 CPABCD（4 位大写字母）合法：按金卡 10% 计算 50/450",
         priority="P2", requirement_ids="REQ-03;REQ-11", case_type="positive",
         method="格式等价类（大写字母类）", test_data="amount=500；coupon=CPABCD；level=gold；points=未勾选",
         steps="1. 在 amount 输入 500 2. 在 coupon 输入 CPABCD 3. level 选择 gold 4. 点击计算",
         expected="discount=50；payable=450（券码视为合法，无券码错误提示）",
         notes="ORACLE-SPEC（R2 字符集 A-Z 合法 + R3 10%）"),
    # --- non functional -----------------------------------------------------
    dict(case_id="TC-CART-030", title="1280x900 视口无横向滚动、结果区计算前后可见、无弹窗且 2 秒内可交互",
         priority="P1", requirement_ids="REQ-12;REQ-13", case_type="nonfunctional",
         method="非功能阈值检查（MS-07）", test_data="amount=500；coupon=CP1234；level=gold；points=未勾选；视口 1280x900",
         steps="1. 以 1280x900 视口打开页面并计时到计算按钮可点击 2. 读取 scrollWidth/clientWidth 与三个输出元素的可见性 3. 输入 500/CP1234/gold 后点击计算 4. 捕获 alert 计数并再次读取输出元素可见性",
         expected="scrollWidth<=clientWidth；discount/payable/message 计算前后均可见；alert 计数=0；load_to_clickable<=2.0s",
         notes="ORACLE-PARTIAL（REQ-12/13 可量化部分）；计时起点为 driver.get 返回到按钮可点击"),
]


def main() -> int:
    columns = ["case_id", "title", "priority", "requirement_ids", "case_type", "method",
               "preconditions", "test_data", "steps", "expected", "actual", "status",
               "automation", "evidence_required", "executed_in_run", "notes"]
    rows = []
    for item in ROWS:
        func = "test_" + item["case_id"].lower().replace("-", "_")
        row = {
            "case_id": item["case_id"],
            "title": item["title"],
            "priority": item["priority"],
            "requirement_ids": item["requirement_ids"],
            "case_type": item["case_type"],
            "method": item["method"],
            "preconditions": PRE,
            "test_data": item["test_data"],
            "steps": item["steps"],
            "expected": item["expected"],
            "actual": "",
            "status": "NOT_RUN",
            "automation": AUT.format(func),
            "evidence_required": "计算后结果区元素截图 + manifest 断言记录（失败时另需整页截图/页面源码/浏览器日志）",
            "executed_in_run": "",
            "notes": item["notes"],
        }
        rows.append(row)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    cases = []
    for row, item in zip(rows, ROWS):
        cases.append({
            "case_id": row["case_id"],
            "requirement_id": row["requirement_ids"],
            "oracle_type": "SPEC" if "ORACLE-SPEC" in item["notes"] else (
                "PARTIAL" if "ORACLE-PARTIAL" in item["notes"] else "DERIVED"),
            "source_ref": item["notes"],
            "expected": row["expected"],
            "judge_rule": "UI 文本精确比较（整数）+ message 字面量比较",
            "test_status": "NOT_RUN",
            "evidence_ref": "",
            "case_type": row["case_type"],
            "method": row["method"],
            "priority": row["priority"],
        })
    OUT_JSON.write_text(json.dumps({"run_id": RUN, "cases": cases}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"wrote {len(rows)} cases -> {OUT_CSV}")
    print(f"wrote {len(cases)} structured cases -> {OUT_JSON}")
    types: dict[str, int] = {}
    for row in rows:
        types[row["case_type"]] = types.get(row["case_type"], 0) + 1
    print("case_type:", types)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
