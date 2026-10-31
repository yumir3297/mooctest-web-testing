"""Page Object for the CartCheck settlement calculator (black-box).

Every locator below was confirmed against the live DOM during
BROWSER_EXPLORATION (`pipeline_runs/RUN-20261031-COLDSTART-01/exploration.json`):
8/8 `data-testid` nodes were found, `discount`/`payable` are `<output>`
elements and `message` is `p.message[role=status]`.  No selector is guessed and
no application source file was read.
"""
from __future__ import annotations

import re
import time

from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

DEFAULT_TARGET = "http://127.0.0.1:8765/"

ALERT_HOOK_JS = """
window.__ccAlertCount = 0;
window.__ccAlertText = [];
window.alert = function (msg) { window.__ccAlertCount += 1; window.__ccAlertText.push(String(msg)); };
window.confirm = function (msg) { window.__ccAlertCount += 1; window.__ccAlertText.push(String(msg)); return true; };
window.prompt = function (msg) { window.__ccAlertCount += 1; window.__ccAlertText.push(String(msg)); return null; };
"""

RESULTS_CONTAINER_JS = """
const ids = ['discount', 'payable', 'message'];
const els = ids.map(function (i) { return document.querySelector('[data-testid="' + i + '"]'); })
               .filter(function (e) { return !!e; });
if (!els.length) { return document.body; }
let node = els[0];
while (node && !els.every(function (e) { return node.contains(e); })) { node = node.parentElement; }
return node || document.body;
"""

SCROLL_JS = """
return {
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  inputsInViewport: ['amount', 'coupon', 'level', 'points', 'calc'].map(function (i) {
    const el = document.querySelector('[data-testid="' + i + '"]');
    if (!el) { return {testid: i, found: false}; }
    const r = el.getBoundingClientRect();
    return {testid: i, found: true, left: Math.round(r.left), right: Math.round(r.right),
            displayed: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)};
  })
};
"""


def normalise_money(text: str) -> int:
    """Parse an output value into an int.

    The requirement does not define a display format, so the comparison is made
    on the numeric value: surrounding spaces and thousands separators are
    removed, anything else (``-``, ``1.5``, ``abc``) raises ``ValueError`` so the
    test reports the raw text instead of silently comparing a wrong value.
    """
    cleaned = re.sub(r"[\s,]", "", text or "")
    if not re.fullmatch(r"-?\d+", cleaned):
        raise ValueError(f"not an integer amount: {text!r}")
    return int(cleaned)


class CartcheckPage:
    """Page Object for the single-page CartCheck calculator."""

    AMOUNT = (By.CSS_SELECTOR, 'input[data-testid="amount"]')
    COUPON = (By.CSS_SELECTOR, 'input[data-testid="coupon"]')
    LEVEL = (By.CSS_SELECTOR, 'select[data-testid="level"]')
    POINTS = (By.CSS_SELECTOR, 'input[data-testid="points"]')
    CALC = (By.CSS_SELECTOR, 'button[data-testid="calc"]')
    DISCOUNT = (By.CSS_SELECTOR, '[data-testid="discount"]')
    PAYABLE = (By.CSS_SELECTOR, '[data-testid="payable"]')
    MESSAGE = (By.CSS_SELECTOR, '[data-testid="message"]')

    def __init__(self, driver: WebDriver, target: str = DEFAULT_TARGET,
                 timeout: float = 10.0) -> None:
        self.driver = driver
        self.target = target
        self.timeout = timeout

    # -- lifecycle ---------------------------------------------------------
    def open(self) -> float:
        """Open the page, wait until the calculate button is clickable.

        Returns the measured ``load -> clickable`` duration in seconds.  The
        measurement uses a monotonic clock only (no fixed waits).
        """
        started = time.monotonic()
        self.driver.get(self.target)
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.CALC)
        )
        elapsed = time.monotonic() - started
        self.install_alert_hook()
        return elapsed

    def reload(self) -> None:
        self.driver.get(self.target)
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.CALC)
        )
        self.install_alert_hook()

    # -- element helpers ---------------------------------------------------
    def wait_visible(self, locator: tuple[str, str],
                     timeout: float | None = None) -> WebElement:
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.visibility_of_element_located(locator)
        )

    def _input(self, locator: tuple[str, str]) -> WebElement:
        element = self.wait_visible(locator)
        element.clear()
        return element

    # -- actions -----------------------------------------------------------
    def set_amount(self, value: str) -> "CartcheckPage":
        element = self._input(self.AMOUNT)
        if value != "":
            element.send_keys(value)
        return self

    def set_coupon(self, value: str) -> "CartcheckPage":
        element = self._input(self.COUPON)
        if value != "":
            element.send_keys(value)
        return self

    def set_level(self, value: str) -> "CartcheckPage":
        select = Select(self.wait_visible(self.LEVEL))
        select.select_by_value(value)
        return self

    def set_points(self, checked: bool) -> "CartcheckPage":
        box = self.wait_visible(self.POINTS)
        if box.is_selected() != checked:
            box.click()
        return self

    def click_calc(self) -> "CartcheckPage":
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.CALC)
        ).click()
        return self

    # -- waits -------------------------------------------------------------
    def wait_for_result(self, timeout: float | None = None) -> str:
        """Wait until an output appears: a number in discount or a message.

        Returns ``"amount"`` when a discount value appeared, ``"message"``
        when only the message was filled, and raises ``TimeoutException``
        otherwise (which the suite classifies as TIMING/LOCATOR, never APP).
        """

        def ready(driver: WebDriver) -> str:
            discount = driver.find_element(*self.DISCOUNT).text.strip()
            message = driver.find_element(*self.MESSAGE).text.strip()
            if discount not in ("", "-"):
                return "amount"
            if message:
                return "message"
            return ""

        return WebDriverWait(self.driver, timeout or self.timeout, poll_frequency=0.05).until(ready)

    # -- observations ------------------------------------------------------
    def discount_text(self) -> str:
        return self.wait_visible(self.DISCOUNT).text.strip()

    def payable_text(self) -> str:
        return self.wait_visible(self.PAYABLE).text.strip()

    def message_text(self) -> str:
        return self.wait_visible(self.MESSAGE).text.strip()

    def outputs_displayed(self) -> dict[str, bool]:
        return {
            name: self.driver.find_element(*locator).is_displayed()
            for name, locator in (("discount", self.DISCOUNT),
                                  ("payable", self.PAYABLE),
                                  ("message", self.MESSAGE))
        }

    def results_container(self) -> WebElement:
        return self.driver.execute_script(RESULTS_CONTAINER_JS)

    def scroll_metrics(self) -> dict:
        return self.driver.execute_script(SCROLL_JS)

    # -- alerts ------------------------------------------------------------
    def install_alert_hook(self) -> None:
        self.driver.execute_script(ALERT_HOOK_JS)

    def alert_count(self) -> int:
        return int(self.driver.execute_script("return window.__ccAlertCount || 0;") or 0)

    def native_alert(self) -> dict:
        """Dismiss a native dialog if one is open and report it."""
        try:
            alert = self.driver.switch_to.alert
        except NoAlertPresentException:
            return {"present": False, "text": ""}
        text = alert.text
        alert.accept()
        return {"present": True, "text": text}
