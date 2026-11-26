#!/usr/bin/env python3
"""Compare manually measured player and prop lengths in like-for-like viewports."""
import argparse
import math


PLAYER_TOLERANCE = 0.05
PROP_TOLERANCE = 0.12


def compare_ratio(observed, expected, limit):
    deviation = observed / expected - 1
    return abs(deviation) <= limit + 1e-9, deviation


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("像素长度须为正数")
    return number


def main():
    parser = argparse.ArgumentParser(description="比较同景别、同类道具、同一测量边缘的单屏尺度。")
    description = "依次填单屏高、人物可见高、门洞净高、第二件参照物高度，也可继续追加参照物"
    parser.add_argument("--reference", required=True, nargs="+", type=positive, help=description)
    parser.add_argument("--sample", required=True, nargs="+", type=positive, action="append",
                        help=description + "。每处单独给一组")
    args = parser.parse_args()
    reference = args.reference
    if len(reference) < 4 or any(len(sample) != len(reference) for sample in args.sample):
        parser.error("每组需要相同的项目顺序与数量，至少比较两件同类场景参照物")

    passed = True
    for index, sample in enumerate(args.sample, 1):
        print(f"单屏样本 {index}")
        lengths = [("角色占屏高", reference[1] / reference[0], sample[1] / sample[0], PLAYER_TOLERANCE)]
        for n in range(2, len(reference)):
            lengths.append((f"参照物 {n-1} / 人高", reference[n] / reference[1],
                            sample[n] / sample[1], PROP_TOLERANCE))
        for label, expected, observed, limit in lengths:
            within, deviation = compare_ratio(observed, expected, limit)
            passed = passed and within
            print(f"  {label}  基准 {expected:.3f}  实测 {observed:.3f}  "
                  f"偏差 {deviation:+.1%}  {'通过' if within else '需复核'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
