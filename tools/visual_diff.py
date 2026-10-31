#!/usr/bin/env python3
"""Visual comparison and annotation helpers.

The tool is intentionally conservative: a pixel difference is a signal for
human review, not proof of a product defect. Dynamic content should be masked
with --ignore-box before interpreting the result.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_rgb(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(path.suffix or ".png", bgr)
    if not ok:
        raise ValueError(f"cannot encode image: {path}")
    buf.tofile(str(path))


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for c in candidates:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        return (255, 0, 0)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _parse_box(value: str, with_label: bool = False) -> dict[str, Any]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) < 4:
        raise ValueError(f"box must be x,y,w,h[,label[,color]]: {value}")
    box: dict[str, Any] = {
        "x": int(parts[0]), "y": int(parts[1]), "w": int(parts[2]), "h": int(parts[3])
    }
    if with_label and len(parts) >= 5 and parts[4]:
        box["label"] = parts[4]
    if with_label and len(parts) >= 6 and parts[5]:
        box["color"] = parts[5]
    return box


def _draw_regions(rgb: np.ndarray, regions: list[dict[str, Any]], label: str = "") -> Image.Image:
    img = Image.fromarray(rgb.copy())
    draw = ImageDraw.Draw(img)
    font = _font(18)
    small = _font(15)
    for i, r in enumerate(regions, 1):
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        color = (255, 45, 45)
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        tag = f"R{i} {w}x{h} area={r.get('area', 0)}"
        tw = draw.textlength(tag, font=small)
        ty = max(0, y - 22)
        draw.rectangle([x, ty, x + tw + 10, ty + 20], fill=(255, 255, 255))
        draw.text((x + 5, ty + 2), tag, fill=(180, 0, 0), font=small)
    if label:
        title_font = _font(22)
        tw = draw.textlength(label, font=title_font)
        draw.rectangle([8, 8, 8 + tw + 16, 40], fill=(0, 0, 0))
        draw.text((16, 12), label, fill=(255, 255, 255), font=title_font)
    return img


def _side_by_side(images: list[tuple[str, np.ndarray]]) -> np.ndarray:
    font = _font(18)
    rendered = []
    for title, img in images:
        pil = Image.fromarray(img)
        draw = ImageDraw.Draw(pil)
        tw = draw.textlength(title, font=font)
        draw.rectangle([0, 0, max(pil.width, int(tw) + 12), 30], fill=(0, 0, 0))
        draw.text((6, 4), title, fill=(255, 255, 255), font=font)
        rendered.append(np.array(pil))
    h = max(x.shape[0] for x in rendered)
    padded = []
    for x in rendered:
        if x.shape[0] < h:
            pad = np.full((h - x.shape[0], x.shape[1], 3), 255, dtype=np.uint8)
            x = np.vstack([x, pad])
        padded.append(x)
    return np.hstack(padded)


def _mask_ignored(mask: np.ndarray, boxes: Iterable[dict[str, Any]]) -> None:
    h, w = mask.shape[:2]
    for b in boxes:
        x, y, bw, bh = b["x"], b["y"], b["w"], b["h"]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w, x + bw), min(h, y + bh)
        if x1 > x0 and y1 > y0:
            mask[y0:y1, x0:x1] = 0


def compare(baseline: Path, actual: Path, out_dir: Path, label: str,
            threshold: int = 30, min_area: int = 40,
            ignore_boxes: list[dict[str, Any]] | None = None,
            fail_on_diff: bool = False) -> dict[str, Any]:
    b = _read_rgb(baseline)
    a = _read_rgb(actual)
    ignore_boxes = ignore_boxes or []
    size_mismatch = b.shape[:2] != a.shape[:2]
    if size_mismatch:
        h = max(b.shape[0], a.shape[0])
        w = max(b.shape[1], a.shape[1])
        bp = np.full((h, w, 3), 255, dtype=np.uint8)
        ap = np.full((h, w, 3), 255, dtype=np.uint8)
        bp[: b.shape[0], : b.shape[1]] = b
        ap[: a.shape[0], : a.shape[1]] = a
        b, a = bp, ap

    diff = cv2.absdiff(b, a)
    gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    raw_mask = (gray > threshold).astype(np.uint8) * 255
    mask = raw_mask.copy()
    _mask_ignored(mask, ignore_boxes)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    regions: list[dict[str, Any]] = []
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < min_area:
            continue
        region_mask = labels == i
        vals = gray[region_mask]
        regions.append({
            "x": x, "y": y, "w": w, "h": h, "area": area,
            "mean_abs_diff": round(float(vals.mean()), 3) if vals.size else 0.0,
            "max_abs_diff": int(vals.max()) if vals.size else 0,
        })
    regions.sort(key=lambda r: r["area"], reverse=True)
    for idx, r in enumerate(regions, 1):
        r["region_id"] = f"R{idx}"

    total_pixels = int(b.shape[0] * b.shape[1])
    raw_changed = int(np.count_nonzero(raw_mask))
    changed = int(np.count_nonzero(mask))
    mse = float(np.mean((b.astype(np.float32) - a.astype(np.float32)) ** 2))
    rmse = math.sqrt(mse)
    psnr = float("inf") if rmse == 0 else 20 * math.log10(255.0 / rmse)
    metrics = {
        "label": label,
        "created_at": now_iso(),
        "baseline": str(baseline),
        "actual": str(actual),
        "size_mismatch": size_mismatch,
        "baseline_size": [int(_read_rgb(baseline).shape[1]), int(_read_rgb(baseline).shape[0])],
        "actual_size": [int(_read_rgb(actual).shape[1]), int(_read_rgb(actual).shape[0])],
        "threshold": threshold,
        "min_area": min_area,
        "ignore_boxes": ignore_boxes,
        "raw_changed_pixels": raw_changed,
        "changed_pixels": changed,
        "total_pixels": total_pixels,
        "diff_ratio": round(changed / total_pixels, 6) if total_pixels else 0.0,
        "mean_abs_diff": round(float(gray.mean()), 4),
        "rmse": round(rmse, 4),
        "psnr": None if math.isinf(psnr) else round(psnr, 4),
        "region_count": len(regions),
        "regions": regions,
        "verdict": "no-change" if changed == 0 else "visual-change-detected",
        "defect_claim": False,
        "defect_note": "Pixel changes are review signals. Confirm with DOM, expected behavior, and reproducible steps before filing a defect.",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    side = _side_by_side([("BASELINE", b), ("ACTUAL", a)])
    _write_rgb(out_dir / "comparison.png", side)
    annotated = _draw_regions(a, regions, label)
    annotated.save(out_dir / "annotated.png")
    _write_rgb(out_dir / "mask.png", np.dstack([mask, mask, mask]))
    heat = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(a, 0.55, heat, 0.45, 0)
    _write_rgb(out_dir / "heatmap.png", overlay)
    _write_rgb(out_dir / "diff.png", diff)

    (out_dir / "regions.json").write_text(
        json.dumps({"label": label, "regions": regions}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if fail_on_diff and changed > 0:
        metrics["exit_code"] = 1
    return metrics


def crop(image: Path, box: dict[str, Any], out: Path) -> dict[str, Any]:
    rgb = _read_rgb(image)
    h, w = rgb.shape[:2]
    x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
    if x < 0 or y < 0 or x + bw > w or y + bh > h:
        raise ValueError(f"crop box outside image: box={(x,y,bw,bh)} image={(w,h)}")
    part = rgb[y:y + bh, x:x + bw]
    _write_rgb(out, part)
    return {"source": str(image), "box": box, "output": str(out),
            "width": int(part.shape[1]), "height": int(part.shape[0])}


def annotate(image: Path, boxes: list[dict[str, Any]], out: Path, label: str = "") -> dict[str, Any]:
    rgb = _read_rgb(image)
    img = Image.fromarray(rgb.copy())
    draw = ImageDraw.Draw(img)
    font = _font(18)
    for b in boxes:
        color = _hex_to_rgb(b.get("color", "#ff2d2d"))
        draw.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]], outline=color, width=3)
        text = b.get("label", "")
        if text:
            tw = draw.textlength(text, font=font)
            draw.rectangle([b["x"], max(0, b["y"] - 24), b["x"] + tw + 10, max(0, b["y"] - 24) + 22],
                           fill=(255, 255, 255))
            draw.text((b["x"] + 5, max(0, b["y"] - 22)), text, fill=color, font=font)
    if label:
        tf = _font(22)
        tw = draw.textlength(label, font=tf)
        draw.rectangle([8, 8, 16 + tw, 42], fill=(0, 0, 0))
        draw.text((14, 12), label, fill=(255, 255, 255), font=tf)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return {"source": str(image), "output": str(out), "boxes": boxes, "label": label}


def inspect(image: Path) -> dict[str, Any]:
    rgb = _read_rgb(image)
    return {
        "path": str(image),
        "width": int(rgb.shape[1]),
        "height": int(rgb.shape[0]),
        "channels": int(rgb.shape[2]),
        "size_bytes": image.stat().st_size,
        "mean_rgb": [round(float(v), 2) for v in rgb.reshape(-1, 3).mean(axis=0)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="visual diff / crop / annotate")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compare")
    p.add_argument("baseline")
    p.add_argument("actual")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--label", default="visual-check")
    p.add_argument("--threshold", type=int, default=30)
    p.add_argument("--min-area", type=int, default=40)
    p.add_argument("--ignore-box", action="append", default=[])
    p.add_argument("--fail-on-diff", action="store_true")
    def _compare(a: argparse.Namespace) -> int:
        boxes = [_parse_box(x) for x in a.ignore_box]
        m = compare(Path(a.baseline), Path(a.actual), Path(a.out_dir), a.label,
                    a.threshold, a.min_area, boxes, a.fail_on_diff)
        print(json.dumps(m, ensure_ascii=False, indent=2))
        return 1 if a.fail_on_diff and m["changed_pixels"] > 0 else 0
    p.set_defaults(func=_compare)

    p = sub.add_parser("crop")
    p.add_argument("image")
    p.add_argument("--box", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=lambda a: print(json.dumps(
        crop(Path(a.image), _parse_box(a.box), Path(a.out)), ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("annotate")
    p.add_argument("image")
    p.add_argument("--box", action="append", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--label", default="")
    p.set_defaults(func=lambda a: print(json.dumps(
        annotate(Path(a.image), [_parse_box(x, True) for x in a.box], Path(a.out), a.label),
        ensure_ascii=False, indent=2)) or 0)

    p = sub.add_parser("inspect")
    p.add_argument("image")
    p.set_defaults(func=lambda a: print(json.dumps(inspect(Path(a.image)), ensure_ascii=False, indent=2)) or 0)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
