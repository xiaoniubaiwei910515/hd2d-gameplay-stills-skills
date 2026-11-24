#!/usr/bin/env python3
"""Composite a Yuwen Yi pose or a left-facing transparent NPC frame on a scene plate."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


ATLAS = Path(__file__).resolve().parents[1] / "assets" / "Yuwen.png"
USER_FRAME = ATLAS.with_name("宇文逸·来图站姿.png")


def dimensions(path):
    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height", "-of", "json", str(path),
    ], text=True)
    streams = json.loads(info)["streams"]
    if not streams:
        raise ValueError(f"找不到图像数据：{path}")
    return streams[0]["width"], streams[0]["height"]


def render(args):
    width, height = dimensions(args.plate)
    if args.foreground and dimensions(args.foreground) != (width, height):
        raise ValueError("透明前景层必须与底图同尺寸")
    actor_height = getattr(args, "height", None)
    if args.sprite:
        source = args.sprite
        source_w, source_h = dimensions(source)
        foot_x, foot_y = args.anchor
        if not (0 <= foot_x <= source_w and 0 <= foot_y <= source_h):
            raise ValueError("脚底锚点超出原精灵画布")
        scale = args.frame_height / source_h
        cell_w, cell_h = round(source_w * scale), args.frame_height
        anchor_x = (source_w - foot_x if args.face == "right" else foot_x) / source_w
        anchor_y = foot_y / source_h
        crop = ""
    elif actor_height is not None:
        # The supplied art faces left. Its two soles are at (8,49) and (17,51)
        # on a 33 × 54 padded canvas; the cape extends behind the foot midpoint.
        source = USER_FRAME
        scale = actor_height / 48
        cell_w, cell_h = round(33 * scale), round(54 * scale)
        anchor_x = (20.5 if args.face == "right" else 12.5) / 33
        anchor_y = 51 / 54
        crop = ""
    else:
        source = ATLAS
        scale = height / 941 * 2 * args.size
        cell_w, cell_h = round(48 * scale), round(56 * scale)
        anchor_x, anchor_y = 0.5, 55 / 56
        crop = f"crop=48:56:{48 * args.pose}:0,"
    if min(cell_w, cell_h) < 1:
        raise ValueError("人物尺寸过小")
    x, y = args.feet
    left, top = x - round(cell_w * anchor_x), y - round(cell_h * anchor_y)
    if not (0 <= left <= width - cell_w and 0 <= top <= height - cell_h):
        raise ValueError("站姿超出画幅，请调整脚底或尺寸")
    red, green, blue = args.tint
    flip = "hflip," if args.face == "right" else ""
    lighting = f"lutrgb=r=val*{red}:g=val*{green}:b=val*{blue}"
    if args.lit_tint:
        side = "X/W" if args.light_from == "right" else "(1-X/W)"
        weight = f"clip(0.85*{side}+0.6*(1-Y/H)-0.19,0,1)"
        channels = []
        for channel, shade, lit in zip("rgb", args.tint, args.lit_tint):
            value = f"{channel}(X,Y)*({shade}+({lit-shade})*{weight})"
            channels.append(f"{channel}='clip({value},0,255)'")
        lighting = "format=gbrap,geq=" + ":".join(channels) + ":a='alpha(X,Y)':interpolation=nearest"
    soften = ""
    if args.soften:
        padding = math.ceil(3 * args.soften)
        soften = (f",format=rgba,pad=iw+{2*padding}:ih+{2*padding}:{padding}:{padding}:color=black@0,"
                  f"format=gbrap,premultiply=inplace=1,gblur=sigma={args.soften}:steps=3,"
                  "unpremultiply=inplace=1,format=rgba")
        left -= padding
        top -= padding
    filters = [
        "[0:v]format=rgb24[plate]",
        f"[1:v]{crop}{flip}"
        f"scale={cell_w}:{cell_h}:flags=neighbor,format=rgba,"
        f"{lighting}{soften}[actor]",
    ]
    # Anchor a tight sole shadow and a softer lobe offset away from the light.
    offset = args.shadow_x
    radius = max(62, abs(offset) + 46)
    local_alpha = (
        f"102*exp(-(((X-{radius + offset})/27)^2+((Y-58-1)/5.0)^2))"
        f"+86*exp(-(((X-{radius})/15)^2+((Y-58)/3.5)^2))"
    )
    if args.sprite:
        local_alpha = (
            f"76*exp(-(((X-{radius+offset})/11)^2+((Y-58)/2.2)^2))"
            f"+134*exp(-(((X-{radius})/6)^2+((Y-58)/1.25)^2))"
        )
    elif actor_height is not None:
        back_x = 4.5 if args.face == "right" else -4.5
        local_alpha = (
            f"65*exp(-(((X-{radius + offset})/13)^2+((Y-58)/2.6)^2))"
            f"+136*exp(-(((X-{radius + back_x})/3.8)^2+((Y-56)/1.0)^2))"
            f"+136*exp(-(((X-{radius - back_x})/3.8)^2+((Y-58)/1.0)^2))"
        )
    shadow_scale = cell_h / 54 if args.sprite else scale
    shadow_w = max(2, 2 * round(radius * shadow_scale / 2))
    shadow_h = max(2, 2 * round(58 * shadow_scale / 2))
    filters.extend([
        f"color=s={2 * radius}x116:c=black:r=1,format=rgba,"
        f"geq=r=19:g=16:b=25:a='{local_alpha}',scale={shadow_w}:{shadow_h}[contact]",
        f"[plate][contact]overlay={x-shadow_w//2}:{y-shadow_h//2}:format=rgb[ground]",
        f"[ground][actor]overlay={left}:{top}:format=rgb[cast]",
    ])
    if args.foreground:
        filters.append("[cast][2:v]overlay=0:0:format=rgb,format=rgb24[final]")
    else:
        filters.append("[cast]format=rgb24[final]")
    command = ["ffmpeg", "-nostdin", "-n", "-loglevel", "error",
               "-i", str(args.plate), "-i", str(source)]
    if args.foreground:
        command.extend(["-i", str(args.foreground)])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".hd2d-cast-", dir=args.output.parent) as tmp:
        staged = Path(tmp) / "frame.png"
        subprocess.run(command + ["-filter_complex", ";".join(filters), "-map", "[final]",
                                  "-frames:v", "1", str(staged)], check=True)
        os.link(staged, args.output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plate", type=Path, help="无主角底图")
    p.add_argument("output", type=Path, help="新的 PNG 路径")
    p.add_argument("--feet", nargs=2, required=True, type=int, metavar=("X", "Y"),
                   help="脚底中心，相对底图左上角的像素坐标")
    p.add_argument("--face", choices=["left", "right"], default="right")
    p.add_argument("--pose", type=int, choices=range(4), help="复现六景时选用的姑苏图集帧")
    sizing = p.add_mutually_exclusive_group()
    sizing.add_argument("--height", type=int, help="使用用户来图站姿，指定发髻到靴底的可见像素高度")
    sizing.add_argument("--size", type=float, default=1, help="复现六景时姑苏图集的相对缩放")
    sizing.add_argument("--frame-height", type=int, help="自定义透明帧缩放后的画布高度，含留边")
    p.add_argument("--sprite", type=Path, help="另一张朝左的 RGBA 透明站姿，--face right 会镜像")
    p.add_argument("--anchor", nargs=2, type=float, metavar=("X", "Y"), help="自定义原帧上的脚底坐标（镜像前）")
    p.add_argument("--tint", nargs=3, type=float, default=(1, 1, 1), metavar=("R", "G", "B"),
                   help="各通道乘数，例如夜渡使用 0.83 0.84 0.91")
    p.add_argument("--lit-tint", nargs=3, type=float, metavar=("R", "G", "B"), help="受光侧乘数，与 --tint 指定的暗部渐变混合")
    p.add_argument("--light-from", choices=["left", "right"], default="left", help="受光方向（画面坐标）")
    p.add_argument("--soften", type=float, default=0, help="远景人物的柔焦半径，单位为成图像素")
    p.add_argument("--shadow-x", type=int, default=0, help="软影的左右偏移，随角色像素格一起缩放")
    p.add_argument("--foreground", type=Path, help="可选同尺寸 RGBA 遮挡层")
    args = p.parse_args()
    npc_options = (args.sprite, args.anchor, args.frame_height)
    if any(v is not None for v in npc_options) and not all(v is not None for v in npc_options):
        p.error("自定义站姿需同时指定 --sprite、--frame-height、--anchor")
    if args.sprite and (args.frame_height <= 0 or args.pose is not None):
        p.error("自定义站姿的画布高度须大于零，--pose 用于姑苏图集")
    if not math.isfinite(args.soften) or args.soften < 0:
        p.error("柔焦半径应为有限的非负数")
    if args.height is not None and (args.height <= 0 or args.pose is not None):
        p.error("来图使用正整数 --height；姑苏图集使用 --pose")
    if args.pose is None:
        args.pose = 0
    if args.output.suffix.lower() != ".png" or args.output.exists():
        p.error("请选择一个未占用的 PNG 输出路径")
    if not all(math.isfinite(v) and v > 0 for v in [args.size, *args.tint, *(args.lit_tint or [])]):
        p.error("尺寸和光色乘数须为有限正数")
    if not all(shutil.which(name) for name in ["ffmpeg", "ffprobe"]):
        p.error("需要可执行的 ffmpeg 和 ffprobe")
    try:
        render(args)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        p.exit(1, f"合成失败：{error}\n")


if __name__ == "__main__":
    main()
