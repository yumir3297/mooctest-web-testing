"""Page Object for the public TodoMVC demo used during acceptance."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TodoPage:
    INPUT = (By.CSS_SELECTOR, "input.new-todo")
    ITEMS = (By.CSS_SELECTOR, ".todo-list li")
    ITEM_TITLE = (By.CSS_SELECTOR, "label[data-testid='todo-title']")
    TOGGLE = (By.CSS_SELECTOR, "input.toggle")
    DESTROY = (By.CSS_SELECTOR, "button.destroy")
    EDIT = (By.CSS_SELECTOR, "input.edit")
    FOOTER = (By.CSS_SELECTOR, "footer.footer")
    COUNT = (By.CSS_SELECTOR, "span.todo-count")
    FILTER_ALL = (By.CSS_SELECTOR, "ul.filters a[href='#/']")
    FILTER_ACTIVE = (By.CSS_SELECTOR, "ul.filters a[href='#/active']")
    FILTER_COMPLETED = (By.CSS_SELECTOR, "ul.filters a[href='#/completed']")
    CLEAR_COMPLETED = (By.CSS_SELECTOR, "button.clear-completed")
    TOGGLE_ALL = (By.CSS_SELECTOR, "input.toggle-all")

    def __init__(self, driver: Chrome, base_url: str, timeout: int = 10) -> None:
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, timeout, poll_frequency=0.2)

    def open(self) -> "TodoPage":
        self.driver.get(self.base_url)
        self.wait.until(EC.visibility_of_element_located(self.INPUT))
        return self

    def add(self, text: str) -> "TodoPage":
        before = len(self.driver.find_elements(*self.ITEMS))
        box = self.wait.until(EC.element_to_be_clickable(self.INPUT))
        box.clear()
        box.send_keys(text)
        box.send_keys(Keys.ENTER)
        if text.strip():
            self.wait.until(lambda d: len(d.find_elements(*self.ITEMS)) == before + 1)
        return self

    def items(self) -> list[WebElement]:
        return self.driver.find_elements(*self.ITEMS)

    def item_texts(self) -> list[str]:
        return [item.text.strip() for item in self.items()]

    def item_title(self, index: int = 0) -> str:
        return self.items()[index].find_element(*self.ITEM_TITLE).text.strip()

    def count_text(self) -> str:
        return self.wait.until(EC.visibility_of_element_located(self.COUNT)).text.strip()

    def toggle(self, index: int = 0) -> "TodoPage":
        item = self.items()[index]
        item.find_element(*self.TOGGLE).click()
        return self

    def toggle_all(self) -> "TodoPage":
        self.wait.until(EC.element_to_be_clickable(self.TOGGLE_ALL)).click()
        return self

    def filter(self, name: str) -> "TodoPage":
        locator = {
            "all": self.FILTER_ALL,
            "active": self.FILTER_ACTIVE,
            "completed": self.FILTER_COMPLETED,
        }[name]
        self.wait.until(EC.element_to_be_clickable(locator)).click()
        return self

    def edit(self, index: int, new_text: str) -> "TodoPage":
        label = self.items()[index].find_element(*self.ITEM_TITLE)
        ActionChains(self.driver).double_click(label).perform()
        edit = self.items()[index].find_element(*self.EDIT)
        self.wait.until(EC.visibility_of(edit))
        edit.send_keys(Keys.CONTROL, "a")
        edit.send_keys(new_text)
        edit.send_keys(Keys.ENTER)
        self.wait.until(lambda d: new_text in self.item_texts())
        return self

    def delete(self, index: int = 0) -> "TodoPage":
        before = len(self.items())
        item = self.items()[index]
        ActionChains(self.driver).move_to_element(item).perform()
        item.find_element(*self.DESTROY).click()
        if before > 1:
            self.wait.until(lambda d: len(d.find_elements(*self.ITEMS)) == before - 1)
        else:
            self.wait.until(lambda d: len(d.find_elements(*self.ITEMS)) == 0)
        return self

    def clear_completed(self) -> "TodoPage":
        self.wait.until(EC.element_to_be_clickable(self.CLEAR_COMPLETED)).click()
        return self

    def footer_visible(self) -> bool:
        return bool(self.driver.find_elements(*self.FOOTER)) and self.driver.find_element(*self.FOOTER).is_displayed()

    def wait_for_empty(self) -> "TodoPage":
        self.wait.until(lambda d: len(d.find_elements(*self.ITEMS)) == 0)
        return self

    def is_item_present(self, text: str) -> bool:
        return any(text in t for t in self.item_texts())

    def wait_for_title(self, text: str) -> "TodoPage":
        self.wait.until(lambda d: text in self.item_texts())
        return self

    def element_screenshot(self, element: WebElement, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not element.screenshot(str(path)):
            raise RuntimeError(f"element screenshot failed: {path}")

    def assert_no_alert(self) -> None:
        try:
            self.driver.switch_to.alert
        except Exception:
            return
        raise AssertionError("unexpected JavaScript alert")
