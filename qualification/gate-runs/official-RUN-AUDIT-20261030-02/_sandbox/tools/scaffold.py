#!/usr/bin/env python3
"""Generate Selenium/pytest skeletons from a test-case CSV.

The generated tests are deliberately explicit skeletons: one function per CSV
row, a case-level expected value, a recorded step, and then
``raise NotImplementedError`` (or ``pytest.skip`` with ``--allow-skip``).
No skeleton ever asserts True.

Usage:
    python tools/scaffold.py --slug cartcheck --target http://127.0.0.1:8765/ \
        --cases reports/test-cases/cartcheck-test-cases.csv \
        --out tests/generated/cartcheck
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates" / "scaffold"

ALIASES = {
    "requirement": "requirement_ids",
    "requirements": "requirement_ids",
    "requirement_id": "requirement_ids",
    "precondition": "preconditions",
    "data": "test_data",
    "steps": "steps",
    "evidence": "evidence_required",
    "case_type": "case_type",
    "priority": "priority",
    "method": "method",
    "expected": "expected",
    "case_id": "case_id",
    "title": "title",
}

CASE_TYPES = {"positive", "negative", "boundary", "state", "combination", "nonfunctional"}


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower()
    return slug or "app"


def _module_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_") or "app"


def _class_name(slug: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", slug) if part]
    camel = "".join(part[:1].upper() + part[1:] for part in parts) or "App"
    if camel[0].isdigit():
        camel = "App" + camel
    return camel + "Page"


def _literal(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _one_line(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _func_name(case_id: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", case_id.lower()).strip("_")
    return "test_" + (name or "case")


def _load_cases(path: Path) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(_read_text(path)))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row")
    header_map: dict[str, str] = {}
    for raw_name in reader.fieldnames:
        name = (raw_name or "").strip()
        header_map[raw_name] = ALIASES.get(name, name)
    if "case_id" not in header_map.values():
        raise ValueError("CSV is missing the required case_id column")
    if "expected" not in header_map.values():
        raise ValueError("CSV is missing the required expected column")

    cases: list[dict[str, str]] = []
    for row in reader:
        if not row or not any((value or "").strip() for value in row.values()):
            continue
        mapped = {header_map.get(key, key): (value or "").strip() for key, value in row.items()}
        case_id = mapped.get("case_id", "")
        if not case_id:
            raise ValueError("CSV contains a row without case_id")
        if not mapped.get("expected", ""):
            raise ValueError(f"case {case_id} has an empty expected value")
        mapped.setdefault("title", "")
        mapped.setdefault("priority", "P2")
        mapped.setdefault("requirement_ids", "UNMAPPED")
        mapped.setdefault("case_type", "positive")
        mapped.setdefault("method", "unspecified")
        mapped.setdefault("steps", "TODO: fill in the steps from the CSV")
        if mapped["case_type"] not in CASE_TYPES:
            raise ValueError(
                f"case {case_id} has invalid case_type {mapped['case_type']!r}; "
                f"expected one of {sorted(CASE_TYPES)}"
            )
        if mapped["priority"] not in {"P0", "P1", "P2", "P3"}:
            raise ValueError(f"case {case_id} has invalid priority {mapped['priority']!r}")
        if not mapped["requirement_ids"]:
            mapped["requirement_ids"] = "UNMAPPED"
        if not mapped["method"]:
            mapped["method"] = "unspecified"
        cases.append(mapped)

    if not cases:
        raise ValueError("CSV contains no data rows")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for case in cases:
        if case["case_id"] in seen:
            duplicates.add(case["case_id"])
        seen.add(case["case_id"])
    if duplicates:
        raise ValueError(f"duplicate case_id(s): {', '.join(sorted(duplicates))}")
    return cases


def _render_test_functions(cases: list[dict[str, str]], allow_skip: bool,
                           cases_rel: str) -> str:
    blocks: list[str] = []
    used: dict[str, int] = {}
    for case in cases:
        base = _func_name(case["case_id"])
        used[base] = used.get(base, 0) + 1
        func_name = base if used[base] == 1 else f"{base}_{used[base]}"
        expected = case["expected"]
        steps = _one_line(case.get("steps", "")) or "TODO: fill in the steps from the CSV"
        message = (
            f"TODO: implement {case['case_id']} - replace this skeleton with real "
            f"waits, actions and assertions (source: {cases_rel})"
        )
        if allow_skip:
            failure = f"    pytest.skip({_literal(message)})"
        else:
            failure = (
                "    raise NotImplementedError(\n"
                f"        {_literal(message)}\n"
                "    )"
            )
        lines = [
            f'@pytest.mark.case_id({_literal(case["case_id"])})',
            f'@pytest.mark.priority({_literal(case["priority"])})',
            f'@pytest.mark.requirement({_literal(case["requirement_ids"])})',
            f'@pytest.mark.method({_literal(case["method"])})',
            f'@pytest.mark.case_type({_literal(case["case_type"])})',
            f'def {func_name}(case_ctx):',
            f'    # 用例标题：{_one_line(case.get("title", "")) or case["case_id"]}',
            f'    case_ctx.set_expected({_literal(expected)})',
            f'    case_ctx.step({_literal("TODO: 按用例步骤执行：" + steps)})',
            failure,
        ]
        blocks.append("\n".join(lines))
    return "\n\n\n".join(blocks) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="generate pytest/page-object skeletons from CSV")
    parser.add_argument("--slug", required=True, help="application slug, e.g. cartcheck")
    parser.add_argument("--target", required=True, help="target URL recorded in the page object")
    parser.add_argument("--cases", required=True, help="test-case CSV path")
    parser.add_argument("--out", default=None, help="output directory (default: tests/generated/<slug>)")
    parser.add_argument("--force", action="store_true", help="overwrite existing generated files")
    parser.add_argument("--allow-skip", action="store_true",
                        help="generate pytest.skip instead of NotImplementedError")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    slug = _slugify(args.slug)
    module_slug = _module_slug(slug)
    cases_path = Path(args.cases)
    cases_path = cases_path if cases_path.is_absolute() else (ROOT / cases_path)
    cases_path = cases_path.resolve()
    if not cases_path.is_file():
        print(f"ERROR: cases CSV not found: {cases_path}", file=sys.stderr)
        return 2
    try:
        cases = _load_cases(cases_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else (ROOT / "tests" / "generated" / slug)
    out_dir = out_dir if out_dir.is_absolute() else (ROOT / out_dir)
    page_path = out_dir / f"page_{module_slug}.py"
    test_path = out_dir / f"test_{module_slug}.py"
    existing = [path for path in (page_path, test_path) if path.exists()]
    if existing and not args.force:
        print("ERROR: generated file(s) already exist; use --force to overwrite:", file=sys.stderr)
        for path in existing:
            print(f"  {path}", file=sys.stderr)
        return 2

    page_template = (TEMPLATE_DIR / "page_object.py.tmpl").read_text(encoding="utf-8")
    test_template = (TEMPLATE_DIR / "test_module.py.tmpl").read_text(encoding="utf-8")
    cases_rel = (cases_path.relative_to(ROOT).as_posix()
                 if cases_path.is_relative_to(ROOT) else str(cases_path).replace("\\", "/"))
    class_name = _class_name(slug)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    page_content = Template(page_template).safe_substitute(
        slug=slug,
        class_name=class_name,
        target=_literal(args.target),
    )
    test_functions = _render_test_functions(cases, args.allow_skip, cases_rel)
    test_content = Template(test_template).safe_substitute(
        slug=slug,
        cases=cases_rel,
        target=args.target,
        generated_at=generated_at,
        page_module=f"page_{module_slug}",
        class_name=class_name,
        test_functions=test_functions,
    )

    _write(page_path, page_content)
    _write(test_path, test_content)
    print(f"generated {len(cases)} test function(s) for {slug}")
    print(f"  page object: {page_path}")
    print(f"  test module: {test_path}")
    print(f"  mode:        {'pytest.skip' if args.allow_skip else 'NotImplementedError'}")
    print(f"  next:        python -m pytest --collect-only -q {test_path.parent}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
