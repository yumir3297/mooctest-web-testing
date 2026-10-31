#!/usr/bin/env python3
"""Register browser/MCP/visual acceptance evidence into the manifest.

The Selenium cases are registered automatically by tests/conftest.py. This
script covers the independent Playwright CLI, Playwright MCP and visual-diff
verification steps used during environment acceptance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import evidence  # noqa: E402

BROWSER = "evidence/raw/RUN-20261029-01/browser"
MCP = "evidence/raw/RUN-20261029-01/mcp"
DIFF = "evidence/diff/RUN-20261029-02/TC-TODO-001-before-after"
ANNOTATED = "evidence/annotated/RUN-20261029-02/TC-TODO-001"


def _norm(path: str) -> str:
    return (ROOT / path).resolve().relative_to(ROOT).as_posix()


def _existing(data: dict, run_id: str, case_id: str, path: str) -> bool:
    normalized = _norm(path)
    return any(
        e.get("run_id") == run_id and e.get("case_id") == case_id and e.get("path") == normalized
        for e in data.get("evidence", [])
    )


def _reg(run_id: str, case_id: str, kind: str, path: str, bucket: str, step: str, caption: str) -> bool:
    p = ROOT / path
    if not p.exists():
        print(f"SKIP missing: {path}")
        return False
    data = evidence.load_manifest()
    if _existing(data, run_id, case_id, path):
        print(f"SKIP existing: {path}")
        return False
    e = evidence.register_evidence(run_id, case_id, kind, path, bucket=bucket, step=step, caption=caption)
    print(f"REGISTERED {e['evidence_id']} {kind} {path}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="RUN-20261029-02")
    args = parser.parse_args(argv)
    run_id = args.run_id

    evidence.update_case(
        run_id, "TC-BROWSER-001",
        title="浏览器探索、交互与截图能力验收",
        status="passed",
        expected="打开 TodoMVC，获取无障碍快照，输入 Acceptance todo，列表出现该文本；视口/整页/元素截图与 MCP 截图均可读取。",
        actual="页面标题 React • TodoMVC；输入后列表出现 Acceptance todo；CLI 与 MCP 截图均为有效 PNG；Playwright MCP 工具列表 25 个。",
        steps=[
            "playwright-cli 打开 https://demo.playwright.dev/todomvc",
            "获取页面无障碍快照并确认输入框 ref",
            "输入 Acceptance todo 并回车",
            "再次获取快照，确认列表出现该文本",
            "保存视口、整页、待办项元素、状态栏元素截图",
            "独立启动 Playwright MCP，调用 browser_navigate、browser_snapshot、browser_take_screenshot",
        ],
        log_path="evidence/logs/RUN-20261029-02/TC-BROWSER-001.log",
    )
    _reg(run_id, "TC-BROWSER-001", "snapshot", f"{BROWSER}/../exploration/snapshot.yml", "raw",
         "exploration", "初始页面无障碍快照")
    _reg(run_id, "TC-BROWSER-001", "snapshot", f"{BROWSER}/../exploration/after-add.yml", "raw",
         "interaction", "新增待办后的无障碍快照")
    _reg(run_id, "TC-BROWSER-001", "screenshot", f"{BROWSER}/viewport.png", "raw",
         "screenshot", "Playwright CLI 视口截图（新增前）")
    _reg(run_id, "TC-BROWSER-001", "fullpage-screenshot", f"{BROWSER}/fullpage.png", "raw",
         "screenshot", "Playwright CLI 整页截图（新增后）")
    _reg(run_id, "TC-BROWSER-001", "element-screenshot", f"{BROWSER}/element-todo-item.png", "raw",
         "element", "待办项元素截图")
    _reg(run_id, "TC-BROWSER-001", "element-screenshot", f"{BROWSER}/element-footer.png", "raw",
         "element", "状态栏元素截图")
    _reg(run_id, "TC-BROWSER-001", "screenshot", f"{MCP}/mcp-screenshot.png", "raw",
         "mcp", "Playwright MCP 截图")
    _reg(run_id, "TC-BROWSER-001", "snapshot", f"{MCP}/mcp-snapshot.yml", "raw",
         "mcp", "Playwright MCP 无障碍快照")
    _reg(run_id, "TC-BROWSER-001", "log", f"{MCP}/mcp-smoke.json", "raw",
         "mcp", "Playwright MCP 工具列表与调用结果")

    evidence.update_case(
        run_id, "TC-VISUAL-001",
        title="截图差异检测、区域定位、裁剪与标注",
        status="passed",
        expected="对同一视口的新增前/后截图返回非零差异像素和差异区域，生成差异图、热力图、对比图、标注图与裁剪图，原始截图保持不变。",
        actual="检测到 8122 个差异像素（0.8813%），5 个差异区域，最大区域 550x15；派生文件已单独保存，原始截图仍保留在 evidence/raw。",
        steps=[
            "用同一视口保存新增待办前后的原始截图",
            "运行 tools/visual_diff.py compare",
            "读取 metrics.json 与 regions.json",
            "生成 annotated/comparison/heatmap/diff 图像",
            "对新增待办区域执行 crop 和中文标注",
            "登记证据并校验 SHA-256",
        ],
        log_path="evidence/logs/RUN-20261029-02/TC-VISUAL-001.log",
    )
    for name, kind, caption in [
        ("annotated.png", "annotation", "差异区域标注图（自动）"),
        ("comparison.png", "comparison", "新增前后并排对比图"),
        ("heatmap.png", "heatmap", "差异热力图"),
        ("diff.png", "diff", "逐像素差异图"),
        ("metrics.json", "metrics", "差异指标"),
        ("regions.json", "regions", "差异区域坐标"),
    ]:
        _reg(run_id, "TC-VISUAL-001", kind, f"{DIFF}/{name}", "diff", "visual-diff", caption)
    _reg(run_id, "TC-VISUAL-001", "annotation", f"{ANNOTATED}/new-item-annotated.png", "annotated",
         "annotation", "新增待办行与状态栏中文标注图")
    _reg(run_id, "TC-VISUAL-001", "crop", f"{ANNOTATED}/new-item-crop.png", "annotated",
         "crop", "新增待办行裁剪图")
    evidence.write_index()
    print(json.dumps(evidence.run_summary(run_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
