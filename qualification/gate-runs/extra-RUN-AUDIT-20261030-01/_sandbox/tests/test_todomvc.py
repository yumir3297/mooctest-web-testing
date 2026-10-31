"""Functional acceptance tests for the public TodoMVC demo."""
from __future__ import annotations

import pytest

from pages.todo_page import TodoPage


@pytest.mark.case_id("TC-TODO-001")
@pytest.mark.acceptance
def test_add_todo(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("打开 TodoMVC 演示页")
    page.open()
    case_ctx.step("在新增输入框中输入 Buy milk 并回车")
    page.add("Buy milk")
    texts = page.item_texts()
    case_ctx.check(texts == ["Buy milk"], "待办列表包含新增项", ["Buy milk"], texts)
    case_ctx.check(page.count_text() == "1 item left", "剩余计数为 1", "1 item left", page.count_text())
    case_ctx.check(page.footer_visible(), "底部状态栏可见", True, page.footer_visible())
    case_ctx.screenshot("新增待办后的元素", element=page.items()[0])
    case_ctx.screenshot("新增待办后的整页", full_page=True)


@pytest.mark.case_id("TC-TODO-002")
@pytest.mark.acceptance
def test_complete_and_filter(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("新增 Task A 与 Task B")
    page.open().add("Task A").add("Task B")
    case_ctx.step("勾选第一条待办")
    page.toggle(0)
    case_ctx.check(page.count_text() == "1 item left", "完成后剩余计数为 1", "1 item left", page.count_text())
    case_ctx.step("切换到 Completed 过滤器")
    page.filter("completed")
    completed = page.item_texts()
    case_ctx.check(completed == ["Task A"], "Completed 仅显示已完成项", ["Task A"], completed)
    case_ctx.step("切换到 Active 过滤器")
    page.filter("active")
    active = page.item_texts()
    case_ctx.check(active == ["Task B"], "Active 仅显示未完成项", ["Task B"], active)
    case_ctx.screenshot("Active 过滤器结果", full_page=True)


@pytest.mark.case_id("TC-TODO-003")
@pytest.mark.acceptance
def test_edit_todo(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("新增 Old title")
    page.open().add("Old title")
    case_ctx.step("双击标题并改为 New title")
    page.edit(0, "New title")
    texts = page.item_texts()
    case_ctx.check(texts == ["New title"], "标题被更新", ["New title"], texts)


@pytest.mark.case_id("TC-TODO-004")
@pytest.mark.acceptance
def test_delete_todo(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("新增 Delete me")
    page.open().add("Delete me")
    case_ctx.step("悬停并点击删除按钮")
    page.delete(0)
    case_ctx.check(page.item_texts() == [], "列表被清空", [], page.item_texts())
    case_ctx.check(not page.footer_visible(), "无待办时底部状态栏隐藏", False, page.footer_visible())
    case_ctx.screenshot("删除后的空列表", full_page=True)


@pytest.mark.case_id("TC-TODO-005")
@pytest.mark.acceptance
def test_empty_and_whitespace_rejected(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    page.open()
    case_ctx.step("直接回车，不输入内容")
    page.add("")
    case_ctx.check(page.item_texts() == [], "空输入不新增待办", [], page.item_texts())
    case_ctx.step("输入三个空格并回车")
    page.add("   ")
    case_ctx.check(page.item_texts() == [], "纯空白输入不新增待办", [], page.item_texts())


@pytest.mark.case_id("TC-TODO-006")
@pytest.mark.acceptance
def test_boundary_lengths(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    page.open()
    case_ctx.step("输入 1 个字符 A")
    page.add("A")
    case_ctx.check(page.item_texts() == ["A"], "1 字符边界被接受", ["A"], page.item_texts())
    case_ctx.step("再输入 200 个字符")
    long_text = "B" * 200
    page.add(long_text)
    case_ctx.check(page.item_texts() == ["A", long_text], "200 字符输入被完整保存", ["A", long_text], page.item_texts())


@pytest.mark.case_id("TC-TODO-007")
@pytest.mark.acceptance
def test_text_is_escaped(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("输入包含 HTML 事件属性的文本")
    payload = "<img src=x onerror=window.__xss=1>"
    page.open().add(payload)
    case_ctx.check(page.item_texts() == [payload], "HTML 文本按纯文本展示", [payload], page.item_texts())
    case_ctx.check(clean_page.execute_script("return window.__xss") is None, "未执行注入脚本", None,
                   clean_page.execute_script("return window.__xss"))
    page.assert_no_alert()
