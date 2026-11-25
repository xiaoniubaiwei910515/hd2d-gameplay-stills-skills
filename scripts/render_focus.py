"""Render a player-focused depth-of-field reference from a finished opaque still."""

import argparse
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image, ImageFilter


def focus_field(size, center, matte):
    width, height = size
    y, x = np.ogrid[:height, :width]
    dx = (x - center[0] * (width - 1)) / (0.20 * width)
    dy = (y - center[1] * (height - 1)) / (0.16 * height)
    distance = np.hypot(dx, dy)
    t = np.clip((distance - 1.0) / 1.35, 0.0, 1.0)
    amount = t * t * (3.0 - 2.0 * t)
    if matte is not None:
        # Scene depth can bring forward defocus in the transition region.
        # Both ends stay anchored, especially the player's untouched near field.
        depth = matte.convert("L").resize(size, Image.Resampling.BILINEAR)
        depth = depth.filter(ImageFilter.GaussianBlur(max(1.0, height / 160)))
        weight = np.asarray(depth, dtype=np.float32) / 255.0
        amount += 0.9 * weight * amount * (1.0 - amount)
    return amount


def smoothstep(start, end, value):
    t = np.clip((value - start) / (end - start), 0, 1)
    return t * t * (3 - 2 * t)


def walking_plane(size, center):
    """Starting field for a traversable middle ground, before object-specific masking."""
    width, height = size
    y, x = np.ogrid[:height, :width]
    dx = x / max(1, width - 1) - center[0]
    dy = y / max(1, height - 1) - center[1]
    side = 0.12 * smoothstep(0.095, 0.50, np.abs(dx))
    back = 0.70 * (1 - smoothstep(-0.40, 0.03, dy))
    front = 0.84 * smoothstep(0.09, 0.50, dy)
    protected = smoothstep(1, 1.45, np.hypot(dx / 0.135, dy / 0.16))
    return np.clip(side + back + front, 0, 1) * protected


def read_focus_map(path, size):
    with Image.open(path) as im:
        if im.size != size:
            raise ValueError("焦带图须与正常版同尺寸")
        if im.mode == "L":
            return np.asarray(im, dtype=np.float64) / 255
        if im.mode.startswith("I;16") or (im.mode == "I" and im.format == "PNG"):
            return np.asarray(im, dtype=np.float64) / 65535
        raise ValueError("请使用 8 位或 16 位灰度焦带图")


def render(source, amount, radius):
    result = source.copy()
    previous = 0.0
    for level in (0.12, 0.28, 0.55, 1.0):
        alpha = np.clip((amount - previous) / (level - previous), 0, 1)
        mask = Image.fromarray(np.rint(255 * alpha).astype(np.uint8))
        blurred = source.filter(ImageFilter.GaussianBlur(radius * level))
        result = Image.composite(blurred, result, mask)
        previous = level
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="正常开发参考 PNG")
    parser.add_argument("output", type=Path, help="独立的景深特效参考 PNG")
    masks = parser.add_mutually_exclusive_group()
    masks.add_argument("--matte", type=Path, help="旧版径向景深的过渡区调节蒙版")
    masks.add_argument("--focus-map", type=Path, help="同尺寸焦带灰度图，黑色保留原像素，白色最虚")
    parser.add_argument("--center", nargs=2, type=float,
                        metavar=("X", "Y"), help="相对于画幅的焦点坐标，默认居中")
    radii = parser.add_mutually_exclusive_group()
    radii.add_argument("--radius", type=float, help="最大模糊半径，单位为最终画幅像素；轻景深默认 900 高时 4.4")
    radii.add_argument("--strength", type=float, help="复现旧版强度倍率，旧版默认值为 1")
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.source, args.matte, args.focus_map) if p}:
        parser.error("输出与输入需使用不同文件")
    if args.focus_map and args.center:
        parser.error("使用焦带图时请在图中确定焦点")
    center = args.center or (0.5, 0.5)
    if not all(0 <= v <= 1 for v in center):
        parser.error("焦点坐标须在 0 至 1 之间")
    if args.strength is not None and not 0 < args.strength <= 4:
        parser.error("强度须大于 0 且不超过 4")
    if args.radius is not None and not (math.isfinite(args.radius) and args.radius > 0):
        parser.error("半径须为有限正数")
    with Image.open(args.source) as im:
        source = im.convert("RGB")
        color_profile = im.info.get("icc_profile")
    legacy = args.matte is not None or args.strength is not None
    if args.focus_map:
        try:
            amount = read_focus_map(args.focus_map, source.size)
        except ValueError as error:
            parser.error(str(error))
    elif args.matte:
        with Image.open(args.matte) as matte:
            amount = focus_field(source.size, center, matte)
    elif legacy:
        amount = focus_field(source.size, center, None)
    else:
        amount = walking_plane(source.size, center)
    radius = args.radius
    if radius is None:
        radius = source.height * 0.016 * (args.strength or 1) if legacy else 4.4 * source.height / 900
    result = render(source, amount, radius)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=args.output.parent, suffix=".png", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        result.save(temp_path, format="PNG", icc_profile=color_profile)
        temp_path.replace(args.output)
    finally:
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
