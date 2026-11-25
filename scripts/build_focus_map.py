"""Build a reusable 16-bit defocus map from visible object silhouettes."""

import argparse
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image

from render_focus import read_focus_map, walking_plane


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="正常版，提供最终画幅尺寸")
    parser.add_argument("output", type=Path, help="合成焦带 PNG")
    base = parser.add_mutually_exclusive_group()
    base.add_argument("--base", type=Path, help="已画好的基础焦带，省略时使用默认行走带")
    base.add_argument("--center", nargs=2, type=float, metavar=("X", "Y"),
                      help="默认行走带中心，范围 0 到 1")
    parser.add_argument("--object", nargs=2, action="append", default=[],
                        metavar=("MASK", "WEIGHT"),
                        help="可见轮廓灰度图及虚化权重 0 到 1，可按从远到近重复")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".png":
        parser.error("焦带输出须使用 .png 扩展名")
    center = args.center or (0.5, 0.5)
    if not all(0 <= v <= 1 for v in center):
        parser.error("行走带中心须在 0 至 1 之间")
    inputs = [args.source] + ([args.base] if args.base else [])
    objects = []
    for filename, value in args.object:
        try:
            weight = float(value)
        except ValueError:
            parser.error(f"物件虚化权重须为数值：{value}")
        if not math.isfinite(weight) or not 0 <= weight <= 1:
            parser.error("物件虚化权重须在 0 至 1 之间")
        path = Path(filename)
        inputs.append(path)
        objects.append((path, weight))
    if args.output.resolve() in {p.resolve() for p in inputs}:
        parser.error("输出与输入须使用不同文件")

    with Image.open(args.source) as image:
        size = image.size
    try:
        amount = read_focus_map(args.base, size) if args.base else walking_plane(size, center)
        for path, weight in objects:
            coverage = read_focus_map(path, size)
            amount += coverage * (weight - amount)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.fromarray(np.rint(65535 * amount).astype(np.uint16))
    with NamedTemporaryFile(dir=args.output.parent, suffix=".png", delete=False) as tmp:
        staged = Path(tmp.name)
    try:
        image.save(staged, format="PNG")
        staged.replace(args.output)
    finally:
        staged.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
