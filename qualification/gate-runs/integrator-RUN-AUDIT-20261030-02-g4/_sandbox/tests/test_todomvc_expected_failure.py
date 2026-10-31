"""A controlled expected failure used to verify the failure-evidence path.

This is not a product defect. The assertion is intentionally wrong, and
pytest.xfail(strict=True) turns the failure into an expected result while the
conftest hook still captures the failure screenshot and logs.
"""
from __future__ import annotations

import pytest

from pages.todo_page import TodoPage


@pytest.mark.case_id("TC-TODO-099")
@pytest.mark.acceptance
@pytest.mark.xfail(strict=True, reason="受控失败：验证失败截图、日志和断言记录链路")
def test_expected_failure_captures_evidence(clean_page, target, case_ctx):
    page = TodoPage(clean_page, target)
    case_ctx.step("新增 Only one")
    page.open().add("Only one")
    case_ctx.step("故意断言剩余计数为 2（实际为 1）")
    case_ctx.check(page.count_text().startswith("2"), "受控失败断言", "2 items left", page.count_text())
