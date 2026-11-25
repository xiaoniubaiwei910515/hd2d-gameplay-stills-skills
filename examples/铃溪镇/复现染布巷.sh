#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo '用法：sh 复现染布巷.sh 输出文件.png' >&2
    exit 2
fi

example_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
layers="$example_dir/分层"
renderer="$example_dir/../../scripts/place_yuwen.py"
work=$(mktemp -d "${TMPDIR:-/tmp}/bellbrook-render.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 1' HUP INT TERM

ffmpeg -nostdin -v error -i "$layers/建筑定稿.png" -i "$layers/景深蒙版.png" \
    -filter_complex '[0:v]format=gbrp,split=2[a][b];[b]gblur=sigma=3.1:steps=3[soft];[1:v]format=gbrp[m];[a][soft][m]maskedmerge,format=rgb24[out]' \
    -map '[out]' -frames:v 1 "$work/plate.png"

# place_yuwen 的 --face left 保留素材朝向，right 水平翻转。按画面从后向前合成。
python3 "$renderer" "$work/plate.png" "$work/apprentice.png" \
    --sprite "$layers/学徒.png" --frame-height 88 --anchor 10.5 37 --feet 611 552 \
    --face right --tint .64 .67 .62 --lit-tint .95 .92 .81 --light-from right --shadow-x -6 --soften .48
python3 "$renderer" "$work/apprentice.png" "$work/dyer.png" \
    --sprite "$layers/染工.png" --frame-height 104 --anchor 12 38 --feet 1063 606 \
    --face left --tint .78 .77 .70 --lit-tint 1.18 1.13 1.02 --light-from right --shadow-x -6 --soften .28
python3 "$renderer" "$work/dyer.png" "$1" \
    --sprite "$layers/旅人.png" --frame-height 115 --anchor 10.5 38 --feet 747 625 \
    --face left --tint .83 .82 .74 --lit-tint 1.27 1.18 1.02 --light-from right --shadow-x -6 --soften .26
