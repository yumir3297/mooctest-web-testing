#!/usr/bin/env python3
"""阶段 → 知识路由表（确定性校验，不是提示词）。

用途：给流水线每个阶段返回**最小**的 Skill / 知识文件 / 规则编号集合，并在启动时
校验所有引用真实存在、规则编号在台账中为 active。任一引用缺失即非零退出。

用法：
    python tools/knowledge_router.py --list-stages
    python tools/knowledge_router.py --stage test-design
    python tools/knowledge_router.py --stage test-design --json

只使用标准库；不联网；不读取被测系统。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".opencode" / "skills"
REGISTRY = REPO_ROOT / "mooctest-knowledge" / "inventory" / "rule_registry.csv"

SKILL_MD = ".opencode/skills/test-design-methodology/SKILL.md"
METHOD = ".opencode/skills/test-design-methodology/references/method_selector.md"
ORACLE = ".opencode/skills/test-design-methodology/references/test_oracle.md"
COVERAGE = ".opencode/skills/test-design-methodology/references/coverage_review.md"
DEFECT = ".opencode/skills/test-design-methodology/references/defect_discovery.md"
OLD_DESIGN = "knowledge/08_derived_rules/test_design_decision_rules.md"
OLD_SCHEMA = "knowledge/08_derived_rules/submission_schema.md"
OLD_NAV = "knowledge/README.md"

# stage -> 路由。skills 只能取 .opencode/skills/ 下真实存在的目录名。
STAGES: dict[str, dict] = {
    "requirement-analysis": {
        "skills": ["test-design-methodology", "test-case-design"],
        "knowledge": ["docs/WORKFLOW.md", METHOD],
        "rules": ["MS-00", "MS-09", "MS-10"],
        "avoid": [
            {
                "path": OLD_DESIGN,
                "replacement": METHOD,
                "reason": "旧速查表的方法矩阵与四点边界已作废",
            }
        ],
        "notes": "只做需求分诊与可测性判定，不产出用例与脚本。",
    },
    "test-design": {
        "skills": ["test-design-methodology", "test-case-design"],
        "knowledge": [SKILL_MD, METHOD, ORACLE],
        "rules": [
            "MS-00", "MS-01", "MS-02", "MS-03", "MS-04", "MS-05",
            "MS-08", "MS-09", "ORA-01", "ORA-02", "ORA-03", "ORA-04",
        ],
        "avoid": [
            {
                "path": OLD_DESIGN,
                "replacement": METHOD,
                "reason": "旧规则要求每边界 min-1/min/max/max+1 四点，MS-01 已改为 2-value/3-value 覆盖项",
            },
            {
                "path": OLD_NAV,
                "replacement": SKILL_MD,
                "reason": "归档导航仍把旧速查表列为设计入口",
            },
        ],
        "notes": "按 MS-00→方法选择→覆盖项→ORA 判据产出用例，不写 Selenium 代码。",
    },
    "case-review": {
        "skills": ["test-design-methodology"],
        "knowledge": [COVERAGE, ORACLE],
        "rules": [
            "REV-00", "REV-01", "REV-02", "REV-03",
            "REV-04", "REV-05", "REV-07", "ORA-04", "ORA-09",
        ],
        "avoid": [
            {
                "path": OLD_SCHEMA,
                "replacement": "docs/CONVENTIONS.md",
                "reason": "旧 TC-WEB-xxx/SHOT-... 命名与现行约定冲突",
            }
        ],
        "notes": "按覆盖项与判据审查，不以用例条数作为通过标准。",
    },
    "browser-exploration": {
        "skills": ["browser-exploration"],
        "knowledge": ["docs/WORKFLOW.md", DEFECT],
        "rules": ["DEF-01", "DEF-06", "DEF-07", "DEF-10"],
        "avoid": [],
        "notes": "探索只确认真实 DOM 与交互路径，结论取证后才回写用例。",
    },
    "script-generation": {
        "skills": ["selenium-testing"],
        "knowledge": ["docs/CONVENTIONS.md", "knowledge/03_selenium_pytest/00_index.md"],
        "rules": ["REV-06", "REV-07", "MS-10"],
        "avoid": [],
        "notes": "以显式等待与稳定定位实现既有用例，不新增需求外断言。",
    },
    "execution": {
        "skills": ["selenium-testing"],
        "knowledge": ["docs/WORKFLOW.md", "docs/CONVENTIONS.md"],
        "rules": ["REV-07", "ORA-09", "MS-10"],
        "avoid": [],
        "notes": "只执行已设计用例并落证据，未跑不得写 PASS。",
    },
    "failure-triage": {
        "skills": ["selenium-testing"],
        "knowledge": ["docs/WORKFLOW.md", ORACLE],
        "rules": ["ORA-08", "ORA-09", "DEF-08", "DEF-10"],
        "avoid": [],
        "notes": "先归因脚本/环境/业务/规格，再决定修脚本或登记缺陷。",
    },
    "visual-evidence": {
        "skills": ["visual-testing"],
        "knowledge": ["docs/CONVENTIONS.md", "docs/WORKFLOW.md"],
        "rules": ["ORA-03", "ORA-07", "DEF-05"],
        "avoid": [],
        "notes": "像素差异只是复核信号，不单独定性为缺陷。",
    },
    "reporting": {
        "skills": ["test-reporting"],
        "knowledge": ["docs/CONVENTIONS.md", COVERAGE],
        "rules": ["REV-00", "REV-04", "REV-09", "ORA-04"],
        "avoid": [],
        "notes": "报告只汇总已执行且有证据的结论，缺口单列。",
    },
    "packaging": {
        "skills": ["mooctest-web-testing", "test-reporting"],
        "knowledge": ["docs/CONVENTIONS.md", "docs/WORKFLOW.md"],
        "rules": ["MS-10", "REV-01", "REV-09"],
        "avoid": [
            {
                "path": OLD_SCHEMA,
                "replacement": "docs/CONVENTIONS.md",
                "reason": "RUN-YYYYMMDD-01 与 SHOT-... 命名已废止，证据命名以现行约定为准",
            }
        ],
        "notes": "按 docs/CONVENTIONS.md 的 ID 与文件布局打包，旧 TC-WEB/SHOT 命名不采用。",
    },
    "quality-gate": {
        "skills": ["mooctest-web-testing"],
        "knowledge": ["docs/WORKFLOW.md", "docs/CONVENTIONS.md", COVERAGE],
        "rules": [
            "MS-09", "REV-00", "REV-01", "REV-02",
            "REV-03", "REV-09", "ORA-04",
        ],
        "avoid": [
            {
                "path": OLD_SCHEMA,
                "replacement": "docs/CONVENTIONS.md",
                "reason": "旧 §6『10 条自动校验』是历史设想，未实现",
            }
        ],
        "notes": "以覆盖项、证据可追溯与未执行状态为门禁项，任一不满足即不通过。",
    },
}

STAGE_ORDER = list(STAGES.keys())


def _skill_frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    block = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    m = re.search(r"^name:\s*(\S+)\s*$", block, re.M)
    return m.group(1) if m else None


def _active_rules() -> set[str]:
    if not REGISTRY.is_file():
        return set()
    active: set[str] = set()
    with REGISTRY.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").strip() == "active":
                active.add((row.get("rule_id") or "").strip())
    return active


def validate() -> list[str]:
    """返回缺失/不一致清单；空列表表示全部引用可解析。"""
    problems: list[str] = []
    active = _active_rules()

    for stage in STAGE_ORDER:
        spec = STAGES[stage]

        if not spec.get("notes"):
            problems.append(f"{stage}: 缺少 notes 边界说明")

        for skill in spec["skills"]:
            skill_md = SKILLS_DIR / skill / "SKILL.md"
            if not skill_md.is_file():
                problems.append(f"{stage}: skill 不存在 -> .opencode/skills/{skill}/SKILL.md")
                continue
            declared = _skill_frontmatter_name(skill_md)
            if declared != skill:
                problems.append(
                    f"{stage}: skill frontmatter name 不一致 -> {skill} (实际 {declared})"
                )

        for rel in spec["knowledge"]:
            if not (REPO_ROOT / rel).is_file():
                problems.append(f"{stage}: knowledge 路径不存在 -> {rel}")

        for item in spec["avoid"]:
            if not (REPO_ROOT / item["path"]).is_file():
                problems.append(f"{stage}: avoid 路径不存在 -> {item['path']}")
            if not (REPO_ROOT / item["replacement"]).is_file():
                problems.append(f"{stage}: avoid 替代路径不存在 -> {item['replacement']}")

        for rule_id in spec["rules"]:
            if not active:
                problems.append(f"{stage}: 规则台账不可用，无法校验 {rule_id}")
                break
            if rule_id not in active:
                problems.append(f"{stage}: 规则编号未在台账中登记为 active -> {rule_id}")

    return problems


def describe(stage: str) -> dict:
    spec = STAGES[stage]
    return {
        "stage": stage,
        "skills": list(spec["skills"]),
        "knowledge": list(spec["knowledge"]),
        "rules": list(spec["rules"]),
        "avoid": [dict(x) for x in spec["avoid"]],
        "notes": spec["notes"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="阶段 → Skill/知识/规则 路由（启动即校验引用是否真实存在）"
    )
    parser.add_argument("--stage", choices=STAGE_ORDER, help="要查询的阶段")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--list-stages", action="store_true", help="列出全部阶段")
    args = parser.parse_args(argv)

    if not args.stage and not args.list_stages:
        parser.error("需要 --stage <stage> 或 --list-stages")

    problems = validate()
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print(f"\n路由校验未通过：缺失或不一致 {len(problems)} 项")
        return 1

    if args.list_stages:
        if args.json:
            print(json.dumps(
                [{"stage": s, "notes": STAGES[s]["notes"]} for s in STAGE_ORDER],
                ensure_ascii=False,
                indent=2,
            ))
        else:
            for s in STAGE_ORDER:
                print(f"{s}\t{STAGES[s]['notes']}")
        return 0

    payload = describe(args.stage)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"stage: {payload['stage']}")
    print("skills:")
    for s in payload["skills"]:
        print(f"  - {s}")
    print("knowledge:")
    for k in payload["knowledge"]:
        print(f"  - {k}")
    print("rules:")
    print("  " + ", ".join(payload["rules"]))
    print("avoid:")
    if payload["avoid"]:
        for a in payload["avoid"]:
            print(f"  - {a['path']} -> {a['replacement']}（{a['reason']}）")
    else:
        print("  （无）")
    print(f"notes: {payload['notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
