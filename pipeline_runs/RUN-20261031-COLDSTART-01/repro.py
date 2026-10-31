"""Independent reproduction probe for the five failing cases.

Runs the same five scenarios in a fresh browser session (not through pytest) so
that "reproduced" is backed by a second, independent execution, and registers
one element screenshot per case.  It asserts nothing: the goal is to record the
observed values and compare them with the requirement by hand.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "RUN-20261031-COLDSTART-01"
TARGET = "http://127.0.0.1:8765/"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests" / "generated" / "cartcheck"))

import evidence  # noqa: E402
from page_cartcheck import CartcheckPage  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.options import Options  # noqa: E402
from selenium.webdriver.chrome.service import Service  # noqa: E402

SCENARIOS = [
    ("TC-CART-002", "800", "CP1234", "silver", False,
     "discount=120；payable=680（需求 E2：银卡 >=800 享 15%）"),
    ("TC-CART-003", "555", "CP1234", "gold", False,
     "discount=55；payable=500（E3：555x0.1=55.5 向下取整）"),
    ("TC-CART-011", "9998", "CP1234", "gold", False,
     "discount=999；payable=8999（9998x0.1=999.8 向下取整）"),
    ("TC-CART-012", "9999", "CP1234", "gold", False,
     "discount=999；payable=9000（9999x0.1=999.9 向下取整）"),
    ("TC-CART-021", "500", "cp1234", "gold", False,
     "message=优惠券码无效；discount=-；payable=-（R2 字符集 ^CP[A-Z0-9]{4}$）"),
]


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-") + f"{int(time.time() * 1000) % 1000:03d}"


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-US")
    service = Service(executable_path=str(ROOT / "tools" / "driver" / "chromedriver.exe"))
    drv = webdriver.Chrome(service=service, options=opts)
    drv.set_page_load_timeout(30)
    return drv


def main() -> int:
    drv = build_driver()
    results = []
    try:
        page = CartcheckPage(drv)
        for case_id, amount, coupon, level, points, expected in SCENARIOS:
            page.open()
            page.set_amount(amount).set_coupon(coupon).set_level(level).set_points(points)
            page.click_calc()
            page.wait_for_result()
            observed = {
                "case_id": case_id,
                "input": {"amount": amount, "coupon": coupon, "level": level, "points": points},
                "expected": expected,
                "discount": page.discount_text(),
                "payable": page.payable_text(),
                "message": page.message_text(),
            }
            out = (ROOT / "evidence" / "raw" / RUN_ID / case_id /
                   f"{case_id}__repro__element__{stamp()}.png")
            out.parent.mkdir(parents=True, exist_ok=True)
            page.results_container().screenshot(str(out))
            entry = evidence.register_evidence(
                RUN_ID, case_id, "element-screenshot",
                str(out.relative_to(ROOT)).replace("\\", "/"), bucket="raw",
                step="repro", caption="独立复现：同一输入再次执行的结果区截图",
            )
            observed["evidence_id"] = entry["evidence_id"]
            observed["screenshot"] = entry["path"]
            results.append(observed)
            print(json.dumps(observed, ensure_ascii=False))
    finally:
        drv.quit()

    out_json = ROOT / "pipeline_runs" / RUN_ID / "repro.json"
    out_json.write_text(json.dumps({"run_id": RUN_ID, "target": TARGET, "results": results},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
