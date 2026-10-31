#!/usr/bin/env python3
"""Register RUN-TOOLCHECK-01 evidence and case summaries."""
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

RUN = "RUN-TOOLCHECK-01"
RAW = f"evidence/raw/{RUN}"
LOGS = f"evidence/logs/{RUN}"
DIFF = f"evidence/diff/{RUN}"
ANN = f"evidence/annotated/{RUN}"


def _norm(path: str) -> str:
    return (ROOT / path).resolve().relative_to(ROOT).as_posix()


def _existing(data: dict, case_id: str, path: str) -> bool:
    normalized = _norm(path)
    return any(
        e.get("run_id") == RUN and e.get("case_id") == case_id and e.get("path") == normalized
        for e in data.get("evidence", [])
    )


def reg(case_id: str, kind: str, path: str, bucket: str, caption: str, step: str = "toolcheck") -> None:
    p = ROOT / path
    if not p.exists():
        print(f"SKIP missing: {path}")
        return
    data = evidence.load_manifest()
    if _existing(data, case_id, path):
        print(f"SKIP existing: {path}")
        return
    e = evidence.register_evidence(RUN, case_id, kind, path, bucket=bucket, step=step, caption=caption)
    print(f"REGISTERED {e['evidence_id']} {case_id} {kind} {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)

    evidence.update_case(
        RUN, "TC-TOOL-BROWSER-001",
        title="Playwright CLI 全链路工具自检",
        status="passed",
        expected="打开 TodoMVC；快照、输入、勾选、悬停、求值、缩放、视口/整页/元素截图、控制台/网络、状态保存、标签页切换均成功。",
        actual="全部成功；items=1 checked=1 count='0 items left'；截图 1280x720/1024x768/550x59 均可读取。",
        steps=[
            "playwright-cli 打开 TodoMVC 并保存快照",
            "输入 Tool check item 并回车",
            "点击 input.toggle 完成待办",
            "悬停待办项并执行 eval 读取计数",
            "缩放到 1024x768，保存视口/整页/元素截图",
            "读取控制台、网络请求、localStorage，保存 storageState",
            "新建 example.com 标签页、切换、关闭",
            "关闭浏览器会话",
        ],
        log_path=f"{LOGS}/TC-TOOL-BROWSER-001.log",
    )
    for name, kind in [
        ("snapshot-before.yml", "snapshot"),
        ("snapshot-after.yml", "snapshot"),
        ("before-viewport.png", "screenshot"),
        ("after-viewport.png", "screenshot"),
        ("after-fullpage.png", "fullpage-screenshot"),
        ("after-element.png", "element-screenshot"),
    ]:
        reg("TC-TOOL-BROWSER-001", kind, f"{RAW}/browser/{name}", "raw", f"Playwright CLI {kind}")
    for name, kind in [
        ("browser-console.log", "log"),
        ("browser-requests.log", "log"),
        ("localstorage.log", "log"),
        ("state.json", "log"),
    ]:
        reg("TC-TOOL-BROWSER-001", kind, f"{LOGS}/{name}", "logs", f"Playwright CLI {kind}")

    evidence.update_case(
        RUN, "TC-TOOL-MCP-001",
        title="Playwright MCP 扩展工具自检",
        status="passed",
        expected="MCP 服务可初始化；navigate/type/wait/find/snapshot/click/evaluate/resize/console/network/tabs/screenshot/close 全部成功。",
        actual="25 个工具；14 个调用步骤全部成功；evaluate 返回 items=1 checked=1 count='0 items left'；截图 1024x768 有效。",
        steps=[
            "启动 Playwright MCP（headless chrome, isolated）",
            "initialize + tools/list",
            "navigate TodoMVC",
            "type + wait_for + find + snapshot",
            "click toggle + evaluate 状态",
            "resize + console + network + tabs",
            "fullPage screenshot + close",
        ],
        log_path=f"{LOGS}/TC-TOOL-MCP-001.log",
    )
    reg("TC-TOOL-MCP-001", "screenshot", f"{RAW}/mcp/mcp-fullpage.png", "raw", "MCP 整页截图")
    reg("TC-TOOL-MCP-001", "snapshot", f"{RAW}/mcp/mcp-snapshot.yml", "raw", "MCP 无障碍快照")
    reg("TC-TOOL-MCP-001", "log", f"{RAW}/mcp/mcp-toolcheck.json", "raw", "MCP 工具调用结果 JSON")

    evidence.update_case(
        RUN, "TC-TOOL-IMAGE-001",
        title="图像 inspect/差异/裁剪/标注工具自检",
        status="passed",
        expected="inspect 读取尺寸；相同图差异为 0；受控差异返回区域；裁剪和中文标注成功；原始图不变。",
        actual="相同图 0 像素/no-change；前后图 7981/921600（0.866%）、6 区域、PSNR 31.0085；裁剪 550x48、标注图生成。",
        steps=[
            "inspect diff-before.png / diff-after.png",
            "compare 相同图 -> no-change",
            "compare 前后图 -> visual-change-detected",
            "crop 新增待办区域",
            "annotate 中文标签",
        ],
        log_path=f"{LOGS}/TC-TOOL-IMAGE-001.log",
    )
    for name in ("diff-before.png", "diff-after.png"):
        reg("TC-TOOL-IMAGE-001", "screenshot", f"{RAW}/browser/{name}", "raw", f"图像工具源图 {name}")
    for sub in ("identical", "changed"):
        for name, kind in [
            ("annotated.png", "annotation"),
            ("comparison.png", "comparison"),
            ("heatmap.png", "heatmap"),
            ("diff.png", "diff"),
            ("mask.png", "mask"),
            ("metrics.json", "metrics"),
            ("regions.json", "regions"),
        ]:
            reg("TC-TOOL-IMAGE-001", kind, f"{DIFF}/{sub}/{name}", "diff", f"{sub} {kind}")
    reg("TC-TOOL-IMAGE-001", "crop", f"{ANN}/image/new-item-crop.png", "annotated", "裁剪图")
    reg("TC-TOOL-IMAGE-001", "annotation", f"{ANN}/image/new-item-annotated.png", "annotated", "中文标注图")

    evidence.update_case(
        RUN, "TC-TOOL-EVIDENCE-001",
        title="证据管理器 CLI 自检",
        status="passed",
        expected="start-run/update-case/add-defect/summary/register/verify/index 均可执行；临时虚拟缺陷在验证后清理。",
        actual="add-defect 在临时运行中生成 1 条虚拟缺陷并统计为 defect_count=1；随后删除临时运行；正式运行未登记产品缺陷。",
        steps=[
            "创建临时运行 RUN-TOOLCHECK-DEFECT",
            "更新虚拟用例并调用 add-defect",
            "summary 显示 defect_count=1",
            "删除临时运行，保留自检日志",
        ],
        log_path=f"{LOGS}/evidence-add-defect.log",
    )
    reg("TC-TOOL-EVIDENCE-001", "log", f"{LOGS}/evidence-add-defect.log", "logs", "add-defect 自检日志")

    evidence.update_case(
        RUN, "TC-TOOL-OPENCODE-001",
        title="OpenCode 当前会话工具自检",
        status="passed",
        expected="skill/task/glob/grep/webfetch/read image 可用；命令文件可枚举；图片可读取。",
        actual="skill visual-testing 加载成功；task explore 返回 6 skills/5 commands；glob 找到命令文件；grep 找到 READY 标记；webfetch 返回 Example Domain；read image 成功显示截图。",
        steps=[
            "加载 visual-testing Skill",
            "glob 枚举 docs 与 .opencode/commands",
            "grep 搜索 READY 标记",
            "webfetch https://example.com",
            "task explore 统计 skills/commands/evidence",
            "read 读取 MCP 截图",
        ],
        log_path=f"{LOGS}/TC-TOOL-OPENCODE-001.log",
    )
    reg("TC-TOOL-OPENCODE-001", "log", f"{LOGS}/TC-TOOL-OPENCODE-001.log", "logs", "当前会话工具自检日志")

    evidence.update_run(
        RUN, status="passed", stage="toolcheck-complete",
        note="工具自检完成：Playwright CLI、Playwright MCP、Selenium、图像工具、证据 CLI、OpenCode 当前会话工具均实际调用成功；未发现产品缺陷。MCP 控制台有 1 个资源加载错误，仅记录，不作为缺陷。",
    )
    evidence.write_index()
    print(json.dumps(evidence.run_summary(RUN), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
