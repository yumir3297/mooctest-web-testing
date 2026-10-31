"""Read-only exploration for CartCheck (cold start).

Opens the real page with Selenium, records the DOM inventory of
``data-testid`` elements, the select options, the real output text formats and
the browser console, then saves two screenshots.  It never writes to the
application, never reads the application source, and only uses locators that
were actually found in the live DOM.

Run from the project root:

    python pipeline_runs/RUN-20261031-COLDSTART-01/explore.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "RUN-20261031-COLDSTART-01"
TARGET = "http://127.0.0.1:8765/"
RAW = ROOT / "evidence" / "raw" / RUN_ID / "EXPLORE"
LOGS = ROOT / "evidence" / "logs" / RUN_ID
OUT = ROOT / "pipeline_runs" / RUN_ID / "exploration.json"


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
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    service = Service(executable_path=str(ROOT / "tools" / "driver" / "chromedriver.exe"))
    drv = webdriver.Chrome(service=service, options=opts)
    drv.set_page_load_timeout(30)
    drv.set_script_timeout(10)
    return drv


INVENTORY_JS = """
const nodes = Array.from(document.querySelectorAll('[data-testid]'));
return nodes.map(function (el) {
  const r = el.getBoundingClientRect();
  const cs = window.getComputedStyle(el);
  let options = null;
  if (el.tagName === 'SELECT') {
    options = Array.from(el.options).map(function (o) {
      return {value: o.value, text: o.textContent.trim(), selected: o.selected};
    });
  }
  return {
    testid: el.getAttribute('data-testid'),
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute('type'),
    role: el.getAttribute('role'),
    name: el.getAttribute('name'),
    id: el.getAttribute('id'),
    cls: el.getAttribute('class'),
    text: (el.tagName === 'INPUT' ? null : (el.textContent || '').trim()),
    value: ('value' in el) ? el.value : null,
    displayed: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
    enabled: !el.disabled,
    rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
    font_size: cs.fontSize,
    color: cs.color,
    options: options
  };
});
"""

OBSERVE_JS = """
const out = {};
['discount','payable','message'].forEach(function (i) {
  const el = document.querySelector('[data-testid="' + i + '"]');
  out[i] = el ? {
    text: (el.textContent || '').trim(),
    displayed: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
    boxes: el.getClientRects().length
  } : null;
});
const amt = document.querySelector('[data-testid="amount"]');
const cpn = document.querySelector('[data-testid="coupon"]');
const lvl = document.querySelector('[data-testid="level"]');
const pts = document.querySelector('[data-testid="points"]');
out.inputs = {
  amount: amt ? amt.value : null,
  coupon: cpn ? cpn.value : null,
  level: lvl ? lvl.value : null,
  points: pts ? pts.checked : null
};
return out;
"""


def observe(drv, label: str) -> dict:
    data = drv.execute_script(OBSERVE_JS)
    data["label"] = label
    return data


def fill(drv, testid: str, value: str) -> None:
    el = drv.find_element(By.CSS_SELECTOR, f'input[data-testid="{testid}"]')
    el.clear()
    el.send_keys(value)


def set_points(drv, checked: bool) -> None:
    el = drv.find_element(By.CSS_SELECTOR, 'input[data-testid="points"]')
    if el.is_selected() != checked:
        el.click()


def click_calc(drv) -> None:
    drv.find_element(By.CSS_SELECTOR, 'button[data-testid="calc"]').click()


def wait_change(drv, before: dict, timeout: float = 3.0) -> str:
    """Wait until any output text changes; never fail the exploration."""

    def changed(d):
        now = d.execute_script(OBSERVE_JS)
        return any(
            (now.get(k) or {}).get("text") != (before.get(k) or {}).get("text")
            for k in ("discount", "payable", "message")
        )

    try:
        WebDriverWait(drv, timeout, poll_frequency=0.05).until(changed)
        return "changed"
    except TimeoutException:
        return "no-change"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    record: dict = {"run_id": RUN_ID, "target": TARGET,
                    "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    states: list[dict] = []
    record["states"] = states
    drv = build_driver()
    try:
        record["window_size"] = drv.get_window_size()
        record["viewport"] = drv.execute_script(
            "return {innerWidth: window.innerWidth, innerHeight: window.innerHeight,"
            " dpr: window.devicePixelRatio,"
            " scrollWidth: document.documentElement.scrollWidth,"
            " clientWidth: document.documentElement.clientWidth,"
            " scrollHeight: document.documentElement.scrollHeight};"
        )

        t0 = time.monotonic()
        drv.get(TARGET)
        WebDriverWait(drv, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="calc"]'))
        )
        record["time_to_interactive_s"] = round(time.monotonic() - t0, 3)

        record["title"] = drv.title
        record["url"] = drv.current_url
        record["page_language"] = drv.execute_script("return document.documentElement.lang || '';")
        record["inventory"] = drv.execute_script(INVENTORY_JS)
        record["body_text"] = drv.find_element(By.TAG_NAME, "body").text

        # ---- state 1: pristine page -------------------------------------
        states.append(observe(drv, "initial"))
        vp = RAW / f"EXPLORE__initial__viewport__{stamp()}.png"
        drv.save_screenshot(str(vp))
        record["screenshot_viewport"] = str(vp.relative_to(ROOT)).replace("\\", "/")

        # ---- interaction 1: documented example E1 ------------------------
        before = observe(drv, "before-E1")
        fill(drv, "amount", "500")
        fill(drv, "coupon", "CP1234")
        Select(drv.find_element(By.CSS_SELECTOR, 'select[data-testid="level"]')).select_by_value("gold")
        click_calc(drv)
        record["e1_wait"] = wait_change(drv, before)
        e1 = observe(drv, "E1 500/CP1234/gold/no-points")
        states.append(e1)
        record["e1_elapsed_s"] = round(time.monotonic() - t0, 3)

        key_el = drv.execute_script(
            """
            const ids = ['amount','coupon','level','points','calc','discount','payable','message'];
            const els = ids.map(function (i) { return document.querySelector('[data-testid="' + i + '"]'); })
                           .filter(function (e) { return !!e; });
            if (!els.length) { return document.body; }
            let node = els[0];
            while (node && !els.every(function (e) { return node.contains(e); })) { node = node.parentElement; }
            return node || document.body;
            """
        )
        key = RAW / f"EXPLORE__e1-result__element__{stamp()}.png"
        key_el.screenshot(str(key))
        record["screenshot_key_area"] = str(key.relative_to(ROOT)).replace("\\", "/")
        record["key_area_tag"] = key_el.tag_name
        record["key_area_testid"] = key_el.get_attribute("data-testid")
        record["key_area_class"] = key_el.get_attribute("class")

        # ---- interaction 2: invalid amount ------------------------------
        before = observe(drv, "before-amount-0")
        fill(drv, "amount", "0")
        click_calc(drv)
        record["amount_0_wait"] = wait_change(drv, before)
        states.append(observe(drv, "amount=0"))

        # ---- interaction 3: invalid coupon ------------------------------
        fill(drv, "amount", "500")
        before = observe(drv, "before-coupon-lower")
        fill(drv, "coupon", "cp1234")
        click_calc(drv)
        record["coupon_lower_wait"] = wait_change(drv, before)
        states.append(observe(drv, "coupon=cp1234"))

        # ---- interaction 4: floor probe ---------------------------------
        fill(drv, "coupon", "CP1234")
        fill(drv, "amount", "555")
        before = observe(drv, "before-555")
        click_calc(drv)
        record["floor_wait"] = wait_change(drv, before)
        states.append(observe(drv, "555 gold"))

        # ---- interaction 5: points flag ---------------------------------
        set_points(drv, True)
        before = observe(drv, "before-555-points")
        click_calc(drv)
        record["points_wait"] = wait_change(drv, before)
        states.append(observe(drv, "555 gold + points"))

        # ---- interaction 6: silver --------------------------------------
        set_points(drv, False)
        fill(drv, "amount", "800")
        Select(drv.find_element(By.CSS_SELECTOR, 'select[data-testid="level"]')).select_by_value("silver")
        before = observe(drv, "before-800-silver")
        click_calc(drv)
        record["silver_wait"] = wait_change(drv, before)
        states.append(observe(drv, "800 silver"))

        # ---- interaction 7: 9999 gold (upper boundary) -------------------
        fill(drv, "amount", "9999")
        Select(drv.find_element(By.CSS_SELECTOR, 'select[data-testid="level"]')).select_by_value("gold")
        before = observe(drv, "before-9999")
        click_calc(drv)
        record["upper_wait"] = wait_change(drv, before)
        states.append(observe(drv, "9999 gold"))

        # ---- console ------------------------------------------------
        try:
            entries = drv.get_log("browser")
        except Exception as exc:  # noqa: BLE001 - exploration must not crash
            entries = [{"level": "N/A", "message": f"console log unavailable: {exc}"}]
        record["console"] = entries
        record["console_errors"] = [e for e in entries
                                    if str(e.get("level")).upper() in ("SEVERE", "ERROR")]

        css = drv.execute_script(
            """
            const out = {};
            ['discount','payable','message'].forEach(function (i) {
              const el = document.querySelector('[data-testid="' + i + '"]');
              if (!el) { return; }
              const r = el.getBoundingClientRect();
              const cs = window.getComputedStyle(el);
              out[i] = {text: (el.textContent||'').trim(), w: Math.round(r.width), h: Math.round(r.height),
                        font: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight,
                        display: cs.display, visibility: cs.visibility};
            });
            return out;
            """
        )
        record["output_style"] = css
        log_path = LOGS / f"EXPLORE__browser__{stamp()}.log"
        log_path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
                            encoding="utf-8")
        record["console_log"] = str(log_path.relative_to(ROOT)).replace("\\", "/")
    except Exception as exc:  # noqa: BLE001 - keep partial exploration evidence
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        drv.quit()
        OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: record.get(k) for k in (
        "title", "url", "window_size", "viewport", "time_to_interactive_s",
        "e1_wait", "amount_0_wait", "coupon_lower_wait", "floor_wait", "console_errors")},
        ensure_ascii=False, indent=2))
    print(json.dumps(states, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
