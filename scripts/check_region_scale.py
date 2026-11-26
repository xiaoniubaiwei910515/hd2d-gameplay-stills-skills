#!/usr/bin/env python3
"""Verify measured player and prop heights in every native viewport of a region."""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from check_scene_scale import PLAYER_TOLERANCE, PROP_TOLERANCE, compare_ratio


def read_span(value, bounds):
    x, top, foot = value
    left, upper, right, bottom = bounds
    if not all(type(n) is int for n in value):
        raise ValueError(f"量点须为整数像素 {value}")
    if not (left <= x < right and upper <= top < foot < bottom):
        raise ValueError(f"量点超出本屏或上下颠倒 {value}, 视口 {bounds}")
    return foot - top


def mark(draw, span, color):
    x, top, bottom = span
    draw.line((x, top, x, bottom), fill=color, width=3)
    for y in (top, bottom):
        draw.line((x - 6, y, x + 6, y), fill=color, width=3)


def reference_ratios(parent, ref):
    with Image.open(parent / ref["image"]) as image:
        bounds = (0, 0, *image.size)
    player = read_span(ref["player"], bounds)
    return player / bounds[3], {name: read_span(span, bounds) / player
                                for name, span in ref["props"].items()}


def verify(path, proof):
    data = json.loads(path.read_text())
    parent = path.parent
    baseline = reference_ratios(parent, data["reference"])
    vx, vy = data["viewport"]
    cols, rows = data["grid"]
    if any(type(n) is not int or n < 1 for n in (vx, vy, cols, rows)):
        raise ValueError("视口尺寸和屏数须为正整数")
    expected = {(c, r) for c in range(1, cols + 1) for r in range(1, rows + 1)}
    seen = set()
    passed = True
    with Image.open(parent / data["image"]) as region:
        if region.size != (vx * cols, vy * rows):
            raise ValueError(f"成图尺寸 {region.size} 与视口及屏数不符")
        overlay = region.convert("RGB") if proof else None
        draw = ImageDraw.Draw(overlay) if overlay else None
        for sample in data["samples"]:
            cell = tuple(sample["cell"])
            if cell in seen or cell not in expected:
                raise ValueError(f"重复或无效的列行 {cell}")
            seen.add(cell)
            c, r = cell
            bounds = ((c - 1) * vx, (r - 1) * vy, c * vx, r * vy)
            ref_player_ratio, props = (reference_ratios(parent, sample["reference"])
                                       if "reference" in sample else baseline)
            human = read_span(sample["player"], bounds)
            ok, error = compare_ratio(human / vy, ref_player_ratio, PLAYER_TOLERANCE)
            results = [f"人高 {human}px ({error:+.1%})"]
            if draw:
                mark(draw, sample["player"], "#f5d569")
            if len(sample["props"]) < 2:
                raise ValueError(f"第 {cell} 屏须量两类当地参照物")
            for key, span in sample["props"].items():
                length = read_span(span, bounds)
                ratio = length / human
                matches, delta = compare_ratio(ratio, props[key], PROP_TOLERANCE)
                ok &= matches
                results.append(f"{key} {length}px / 人高 {ratio:.2f} ({delta:+.1%})")
                if draw:
                    mark(draw, span, "#67eecf" if matches else "#ff5353")
            print(f"{c}列{r}排  {'通过' if ok else '需复核'}  " + "，".join(results))
            passed &= ok
        if expected != seen:
            raise ValueError(f"缺少视口 {sorted(expected - seen)}")
        if proof:
            overlay.save(proof)
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurements", type=Path, help="原图、视口与量点 JSON")
    parser.add_argument("--proof", type=Path, help="输出原尺寸带量线的验收图")
    args = parser.parse_args()
    try:
        if args.proof:
            sources = json.loads(args.measurements.read_text())
            inputs = [args.measurements, args.measurements.parent / sources["image"],
                      args.measurements.parent / sources["reference"]["image"]]
            inputs.extend(args.measurements.parent / sample["reference"]["image"]
                          for sample in sources["samples"] if "reference" in sample)
            if args.proof.resolve() in {p.resolve() for p in inputs}:
                raise ValueError("量线图须另存")
        return 0 if verify(args.measurements, args.proof) else 1
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"比例记录无效：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
