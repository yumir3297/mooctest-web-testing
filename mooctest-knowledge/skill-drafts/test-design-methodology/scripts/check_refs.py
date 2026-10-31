#!/usr/bin/env python3
"""Skill 依赖自检：校验 references 齐全、版本一致、规则台账可解析。

用法（在任意目录执行均可，路径以本文件为锚点解析）：
    python scripts/check_refs.py            # 退出码 0=全部通过，1=有问题

只使用标准库，不联网、不读取教材。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REFERENCES = SKILL_DIR / "references"
REQUIRED = [
    "method_selector.md",
    "test_oracle.md",
    "coverage_review.md",
    "defect_discovery.md",
    "sources_index.md",
]
# 规则台账位于仓库内，不在 Skill 包内；缺失时只警告，不判失败。
REGISTRY_CANDIDATES = [
    SKILL_DIR.parent.parent / "inventory" / "rule_registry.csv",
    SKILL_DIR.parents[2] / "mooctest-knowledge" / "inventory" / "rule_registry.csv",
]


def read_version(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^version:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not SKILL_DIR.is_dir():
        print(f"[FAIL] Skill 目录不存在: {SKILL_DIR}")
        return 1

    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.is_file():
        errors.append("缺少 SKILL.md")
    else:
        version = read_version(skill_md)
        if version is None:
            errors.append("SKILL.md 缺少 version frontmatter")
        else:
            print(f"[OK]   SKILL.md version = {version}")

    for name in REQUIRED:
        p = REFERENCES / name
        if p.is_file() and p.stat().st_size > 0:
            print(f"[OK]   references/{name} ({p.stat().st_size} bytes)")
        else:
            errors.append(f"references/{name} 缺失或为空")

    # 台账解析：active 规则的 canonical_file 必须存在
    registry = next((p for p in REGISTRY_CANDIDATES if p.is_file()), None)
    if registry is None:
        warnings.append("未找到 rule_registry.csv（Skill 独立分发时可忽略）")
    else:
        active = 0
        with registry.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("status") or "").strip() != "active":
                    continue
                active += 1
                rel = (row.get("canonical_file") or "").strip()
                if not rel:
                    errors.append(f"{row.get('rule_id')}: active 规则缺少 canonical_file")
                    continue
                target = SKILL_DIR / rel
                if not target.is_file():
                    errors.append(f"{row.get('rule_id')}: canonical_file 不存在 -> {rel}")
        print(f"[OK]   rule_registry.csv 解析完成，active 规则 {active} 条")

    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[FAIL] {e}")

    print(f"\n结果: {'通过' if not errors else '未通过'}（errors={len(errors)}, warnings={len(warnings)}）")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
