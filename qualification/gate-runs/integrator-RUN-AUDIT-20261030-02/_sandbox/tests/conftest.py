"""Pytest integration: Selenium, explicit waits, logs and failure evidence.

Schema v1.1 behaviour:
- case level ``expected`` / ``actual`` are only written by
  :meth:`CaseContext.set_expected` / :meth:`CaseContext.set_actual`. A single
  assertion no longer overwrites the case level oracle.
- a driver/browser major version mismatch is a hard, explicit failure instead of
  a silent downgrade.
- setup phase failures are recorded as ``blocked`` so an environment problem is
  never reported as a product defect.
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import evidence  # noqa: E402
import versioning  # noqa: E402

DEFAULT_TARGET = "https://demo.playwright.dev/todomvc"
CASE_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe(value: str) -> str:
    return CASE_SAFE.sub("-", value).strip("-") or "case"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"


def _case_id(node: pytest.Item) -> str:
    marker = node.get_closest_marker("case_id")
    if marker and marker.args:
        return _safe(str(marker.args[0]))
    return _safe(node.nodeid.replace("::", "-"))


def _compat_report() -> dict[str, str]:
    chrome = versioning.find_chrome()
    driver = ROOT / "tools" / "driver" / "chromedriver.exe"
    chrome_version = versioning.exe_version(chrome) if chrome else "<not found>"
    driver_version = versioning.exe_version(driver) if driver.is_file() else "<not found>"
    return {
        "chrome_path": str(chrome) if chrome else "",
        "chrome_version": chrome_version,
        "chromedriver_path": str(driver) if driver.is_file() else "",
        "chromedriver_version": driver_version,
    }


def _assert_major_match(info: dict[str, str]) -> None:
    chrome_major = versioning.major(info["chrome_version"])
    driver_major = versioning.major(info["chromedriver_version"])
    if chrome_major is None or driver_major is None:
        raise RuntimeError(
            "driver compatibility check could not determine a version: "
            f"chrome={info['chrome_version']!r} chromedriver={info['chromedriver_version']!r}"
        )
    if chrome_major != driver_major:
        raise RuntimeError(
            "Chrome/ChromeDriver major version mismatch: "
            f"Chrome {info['chrome_version']} vs ChromeDriver {info['chromedriver_version']}. "
            "Run `python tools/env_check.py` and install a matching driver."
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-id", action="store", default=os.environ.get("MOOCTEST_RUN_ID", ""),
                     help="evidence run id (default: RUN-<timestamp>)")
    parser.addoption("--target", action="store", default=os.environ.get("MOOCTEST_TARGET", DEFAULT_TARGET),
                     help="target web application URL")
    parser.addoption("--capture-pass", action="store_true", default=os.environ.get("MOOCTEST_CAPTURE_PASS") == "1",
                     help="also save a final screenshot for passing tests")
    parser.addoption("--headed", action="store_true", default=os.environ.get("MOOCTEST_HEADED") == "1",
                     help="run Chrome in headed mode")
    parser.addoption("--suite-label", action="store", default=os.environ.get("MOOCTEST_SUITE_LABEL", ""),
                     help="free form label describing the suite under test")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "case_id(id): evidence case id")
    config.addinivalue_line("markers", "acceptance: acceptance test")
    config.addinivalue_line("markers", "requirement(id): requirement id traced by this case")
    config.addinivalue_line("markers", "method(name): test design method used")
    config.addinivalue_line("markers", "priority(level): P0/P1/P2")
    config.addinivalue_line("markers", "case_type(kind): positive/negative/boundary/state/combination")
    run_id = config.getoption("--run-id") or f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    target = config.getoption("--target")
    evidence.ensure_layout()
    existing = evidence.load_manifest().get("runs", {})
    label = config.getoption("--suite-label") or ("pytest Selenium acceptance" if run_id not in existing else "")
    compat = _compat_report()
    env = {
        "python": sys.version.split()[0],
        "platform": f"{sys.platform}",
        "chrome": compat["chrome_version"],
        "chromedriver": compat["chromedriver_version"],
        "target": target,
    }
    try:
        import selenium as _selenium
        env["selenium"] = _selenium.__version__
    except Exception:
        env["selenium"] = "<import failed>"
    try:
        env["pytest"] = pytest.__version__
    except Exception:
        env["pytest"] = "<unknown>"
    evidence.start_run(run_id, target=target, label=label, reuse=True, environment=env)
    config._mooctest = {  # type: ignore[attr-defined]
        "run_id": run_id,
        "target": target,
        "capture_pass": bool(config.getoption("--capture-pass")),
        "headed": bool(config.getoption("--headed")),
        "results": [],
        "compat": compat,
        "started_at": time.time(),
    }
    log_dir = evidence.LOGS_DIR / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "pytest.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    config._mooctest["log_handler"] = handler  # type: ignore[attr-defined]
    logging.getLogger("mooctest").info(
        "run_id=%s target=%s chrome=%s driver=%s",
        run_id, target, compat["chrome_version"], compat["chromedriver_version"],
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    cfg = getattr(session.config, "_mooctest", None)
    if not cfg:
        return
    results = cfg["results"]
    call_results = [r for r in results if r.get("when") == "call"]
    failed = any(r.get("outcome") == "failed" for r in call_results)
    blocked = any(r.get("outcome") == "blocked" for r in results)
    xfailed = any(r.get("wasxfail") for r in call_results)
    total = len(results)
    if failed:
        status = "failed"
    elif blocked and not any(r.get("outcome") == "passed" for r in call_results):
        status = "blocked"
    elif total:
        status = "passed"
    else:
        status = "blocked"
    note = (f"pytest exit={exitstatus}; total={total}; failed={failed}; "
            f"blocked={blocked}; xfailed={xfailed}")
    evidence.update_run(cfg["run_id"], status=status, stage="report-ready", note=note)
    handler = cfg.get("log_handler")
    if handler:
        logging.getLogger().removeHandler(handler)
        handler.close()


def _marker_meta(item: pytest.Item) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for name, key in (("requirement", "requirement_ids"), ("method", "method"),
                      ("priority", "priority"), ("case_type", "case_type")):
        marker = item.get_closest_marker(name)
        if marker and marker.args:
            meta[key] = str(marker.args[0])
    return meta


def pytest_runtest_setup(item: pytest.Item) -> None:
    cfg = item.config._mooctest  # type: ignore[attr-defined]
    cid = _case_id(item)
    item._mooctest_case_id = cid  # type: ignore[attr-defined]
    item._mooctest_start = time.time()  # type: ignore[attr-defined]
    evidence.update_case(cfg["run_id"], cid, title=item.name, status="running", meta=_marker_meta(item))


def _capture_viewport(driver: webdriver.Chrome, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not driver.save_screenshot(str(path)):
        raise RuntimeError(f"viewport screenshot failed: {path}")


def _capture_fullpage(driver: webdriver.Chrome, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
    size = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
    width = int(math.ceil(float(size.get("width", driver.get_window_size()["width"]))))
    height = int(math.ceil(float(size.get("height", driver.get_window_size()["height"]))))
    height = min(height, 12000)
    result = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": True,
        "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
    })
    path.write_bytes(base64.b64decode(result["data"]))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _browser_log(driver: webdriver.Chrome) -> str:
    try:
        entries = driver.get_log("browser")
    except Exception as exc:
        return f"browser log unavailable: {exc}\n"
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"


def _register(driver: webdriver.Chrome, cfg: dict[str, Any], case_id: str, kind: str,
              path: Path, step: str, caption: str) -> None:
    rel = path.relative_to(ROOT).as_posix()
    evidence.register_evidence(cfg["run_id"], case_id, kind, rel, bucket="raw",
                               step=step, caption=caption)


def _capture_failure(driver: webdriver.Chrome, cfg: dict[str, Any], case_id: str,
                     case_dir: Path, log_dir: Path, ts: str) -> None:
    try:
        view = case_dir / f"{case_id}__failure__viewport__{ts}.png"
        _capture_viewport(driver, view)
        _register(driver, cfg, case_id, "screenshot", view, "failure", "失败时视口截图")
    except Exception as exc:
        logging.getLogger("mooctest").warning("failure viewport capture failed: %s", exc)
    try:
        full = case_dir / f"{case_id}__failure__fullpage__{ts}.png"
        _capture_fullpage(driver, full)
        _register(driver, cfg, case_id, "fullpage-screenshot", full, "failure", "失败时整页截图")
    except Exception as exc:
        logging.getLogger("mooctest").warning("failure fullpage capture failed: %s", exc)
    try:
        src = case_dir / f"{case_id}__failure__page-source__{ts}.html"
        _write_text(src, driver.page_source)
        _register(driver, cfg, case_id, "page-source", src, "failure", "失败时页面源码")
    except Exception as exc:
        logging.getLogger("mooctest").warning("page source capture failed: %s", exc)
    try:
        blog = log_dir / f"{case_id}__browser__{ts}.log"
        _write_text(blog, _browser_log(driver))
        rel = blog.relative_to(ROOT).as_posix()
        evidence.register_evidence(cfg["run_id"], case_id, "log", rel, bucket="logs",
                                   step="failure", caption="失败时浏览器控制台日志")
    except Exception as exc:
        logging.getLogger("mooctest").warning("browser log capture failed: %s", exc)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()
    cfg = item.config._mooctest  # type: ignore[attr-defined]
    case_id = getattr(item, "_mooctest_case_id", _case_id(item))
    start = getattr(item, "_mooctest_start", time.time())
    duration_ms = int((time.time() - start) * 1000)
    driver = item.funcargs.get("driver")
    case_dir = evidence.RAW_DIR / cfg["run_id"] / case_id
    log_dir = evidence.LOGS_DIR / cfg["run_id"]
    case_log = log_dir.joinpath(f"{case_id}.log").relative_to(ROOT).as_posix()

    if report.when == "setup" and report.failed:
        cfg["results"].append({
            "nodeid": report.nodeid, "outcome": "blocked", "when": "setup",
            "wasxfail": None, "duration": report.duration,
        })
        reason = str(report.longrepr)[:2000] if report.longrepr else "setup failed"
        evidence.update_case(
            cfg["run_id"], case_id, status="blocked",
            actual=f"BLOCKED（环境/夹具失败，不计为产品缺陷）：{reason}",
            log_path=case_log, duration_ms=duration_ms,
            meta={"failure_class": "ENV"},
        )
        return

    if report.when != "call":
        return

    cfg["results"].append({
        "nodeid": report.nodeid,
        "outcome": report.outcome,
        "when": "call",
        "wasxfail": getattr(report, "wasxfail", None),
        "duration": report.duration,
    })
    is_xfail = hasattr(report, "wasxfail")
    if report.failed or is_xfail:
        status = "xfailed" if is_xfail else "failed"
        actual = (str(report.longrepr) if report.longrepr else "断言失败")[:4000]
        if driver is not None:
            _capture_failure(driver, cfg, case_id, case_dir, log_dir, _stamp())
        evidence.update_case(
            cfg["run_id"], case_id, status=status, actual=actual,
            log_path=case_log, duration_ms=duration_ms,
            meta={"failure_class": "ASSERT" if status == "failed" and not is_xfail else status.upper()},
        )
    elif report.passed:
        if cfg.get("capture_pass") and driver is not None:
            ts = _stamp()
            try:
                shot = case_dir / f"{case_id}__final__viewport__{ts}.png"
                _capture_viewport(driver, shot)
                _register(driver, cfg, case_id, "screenshot", shot, "final", "通过后的最终视口截图")
            except Exception as exc:
                logging.getLogger("mooctest").warning("pass screenshot failed: %s", exc)
        evidence.update_case(cfg["run_id"], case_id, status="passed",
                             log_path=case_log, duration_ms=duration_ms)
    elif report.skipped:
        evidence.update_case(cfg["run_id"], case_id, status="skipped",
                             actual=str(report.longrepr)[:1000] if report.longrepr else "skipped",
                             log_path=case_log, duration_ms=duration_ms)


@pytest.fixture(scope="session")
def run_id(pytestconfig: pytest.Config) -> str:
    return pytestconfig._mooctest["run_id"]  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def target(pytestconfig: pytest.Config) -> str:
    return pytestconfig._mooctest["target"]  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def driver(pytestconfig: pytest.Config):
    cfg = pytestconfig._mooctest  # type: ignore[attr-defined]
    compat = cfg.get("compat") or _compat_report()
    _assert_major_match(compat)
    opts = Options()
    if not cfg.get("headed"):
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-US")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver_path = ROOT / "tools" / "driver" / "chromedriver.exe"
    service = Service(executable_path=str(driver_path)) if driver_path.exists() else Service()
    d = webdriver.Chrome(service=service, options=opts)
    browser_version = d.capabilities.get("browserVersion", "")
    driver_version = (d.capabilities.get("chrome") or {}).get("chromedriverVersion", "")
    logging.getLogger("mooctest").info(
        "Chrome session created: browser=%s driver=%s", browser_version, driver_version)
    browser_major = versioning.major(browser_version)
    driver_major = versioning.major(driver_version)
    if browser_major is not None and driver_major is not None and browser_major != driver_major:
        try:
            d.quit()
        finally:
            raise RuntimeError(
                "session created but browser/driver major mismatch: "
                f"{browser_version} vs {driver_version}"
            )
    d.set_page_load_timeout(30)
    d.set_script_timeout(10)
    try:
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass
        logging.getLogger("mooctest").info("Chrome session closed")


@pytest.fixture()
def clean_page(driver, target) -> webdriver.Chrome:
    driver.get(target)
    driver.execute_script("window.localStorage.clear();")
    driver.refresh()
    return driver


@pytest.fixture()
def case_id(request: pytest.FixtureRequest) -> str:
    return getattr(request.node, "_mooctest_case_id", _case_id(request.node))


class CaseContext:
    def __init__(self, driver: webdriver.Chrome, run_id_value: str, case_id_value: str) -> None:
        self.driver = driver
        self.run_id = run_id_value
        self.case_id = case_id_value
        self.steps: list[str] = []
        self.assertions: list[dict[str, Any]] = []
        self.log_path = evidence.LOGS_DIR / run_id_value / f"{case_id_value}.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"mooctest.case.{case_id_value}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = logging.FileHandler(self.log_path, encoding="utf-8")
        self.handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(self.handler)
        self.logger.info("case=%s run=%s", case_id_value, run_id_value)

    def step(self, text: str) -> None:
        self.steps.append(text)
        self.logger.info("STEP %s", text)
        evidence.update_case(self.run_id, self.case_id, steps=self.steps,
                             log_path=self.log_path.relative_to(ROOT).as_posix())

    def set_expected(self, text: str) -> None:
        """Declare the case level expected result (never derived from assertions)."""
        evidence.update_case(self.run_id, self.case_id, expected=str(text))

    def set_actual(self, text: str) -> None:
        """Declare the case level observed result."""
        evidence.update_case(self.run_id, self.case_id, actual=str(text))

    def note(self, text: str) -> None:
        evidence.update_case(self.run_id, self.case_id, notes=text)

    def check(self, condition: bool, name: str, expected: Any, actual: Any) -> None:
        passed = bool(condition)
        rec = {"name": name, "expected": str(expected), "actual": str(actual),
               "passed": passed, "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
        self.assertions.append(rec)
        self.logger.info("CHECK %s passed=%s expected=%r actual=%r", name, passed, expected, actual)
        evidence.update_case(self.run_id, self.case_id,
                             assertions=self.assertions, steps=self.steps,
                             log_path=self.log_path.relative_to(ROOT).as_posix())
        if not passed:
            raise AssertionError(f"{name}: expected={expected!r} actual={actual!r}")

    def screenshot(self, caption: str, element=None, full_page: bool = False) -> Path:
        ts = _stamp()
        kind = "element-screenshot" if element is not None else ("fullpage-screenshot" if full_page else "screenshot")
        tag = "element" if element is not None else ("fullpage" if full_page else "viewport")
        out = evidence.RAW_DIR / self.run_id / self.case_id / f"{self.case_id}__{_safe(caption)}__{tag}__{ts}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        if element is not None:
            if not element.screenshot(str(out)):
                raise RuntimeError(f"element screenshot failed: {out}")
        elif full_page:
            _capture_fullpage(self.driver, out)
        else:
            _capture_viewport(self.driver, out)
        rel = out.relative_to(ROOT).as_posix()
        evidence.register_evidence(self.run_id, self.case_id, kind, rel, bucket="raw",
                                   step=caption, caption=f"用例证据：{caption}")
        self.logger.info("SCREENSHOT %s", rel)
        return out

    def close(self) -> None:
        try:
            self.logger.removeHandler(self.handler)
            self.handler.close()
        except Exception:
            pass


@pytest.fixture()
def case_ctx(driver, run_id, case_id):
    ctx = CaseContext(driver, run_id, case_id)
    try:
        yield ctx
    finally:
        evidence.update_case(run_id, case_id, steps=ctx.steps, assertions=ctx.assertions,
                             log_path=ctx.log_path.relative_to(ROOT).as_posix())
        ctx.close()
