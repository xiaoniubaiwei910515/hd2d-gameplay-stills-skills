# HD-2D 武侠实机图工作流

这是一个可直接安装的 Codex 技能。它从同一张场景底图分别生成正午、黄昏和夜晚，再把同一套像素人物放回固定位置。下面三张是柳荫渡口的修订成图，点击可看原尺寸。

| 正午 | 黄昏 | 夜晚 |
|:---:|:---:|:---:|
| [![正午](examples/柳荫渡口/01_正午.png)](examples/柳荫渡口/01_正午.png) | [![黄昏](examples/柳荫渡口/02_黄昏.png)](examples/柳荫渡口/02_黄昏.png) | [![夜晚](examples/柳荫渡口/03_夜晚.png)](examples/柳荫渡口/03_夜晚.png) |

## 在 Codex 中使用

下载或克隆整个仓库，将含有 `SKILL.md` 的仓库根目录作为 `hd2d-gameplay-stills` 放入 Codex 技能目录。默认位置是 `~/.codex/skills/hd2d-gameplay-stills/`；自定义了 `CODEX_HOME` 时，安装到其 `skills/` 下。新开一个 Codex 会话即可点名使用。也可以在仓库目录中直接指定 [SKILL.md](SKILL.md)。

> 用 $hd2d-gameplay-stills 生成同一处江南渡口的正午、黄昏、夜晚三张图。正午让日光透过柳枝落到石阶，三个时段使用相同的机位、人物站位和朝向。

生成新的环境或角色需要 Codex 会话提供图像生成功能。使用随包 PNG 本地合成只需 Python 3、FFmpeg 和 ffprobe。从仓库根目录运行以下命令，即可在 `renders/` 中得到一张示例图。脚本会创建输出目录，并保留已有的同名图。

```sh
python3 scripts/place_yuwen.py 'assets/渡口·正午无人底图.png' 'renders/正午-宇文逸.png' \
  --height 124 --feet 752 638 --face right \
  --tint .86 .87 .77 --lit-tint 1.23 1.14 .93 --shadow-x 4
```

## 按用途查找

| 想做什么 | 从哪里开始 |
|---|---|
| 换地点，生成自己的场景 | [技能入口](SKILL.md) · [中文主提示词与 NPC 模板](references/出图主提示词.md) |
| 按渡口修订案重新出图 | [实际英文提示词和每次附图的顺序](examples/柳荫渡口/生图提示词.md) · [三张成图与生成底图](examples/柳荫渡口/) |
| 用现成素材合成主角与三名 NPC | [四人站位与完整命令](references/柳荫渡口复盘.md) · [透明人物和底图](assets/) |
| 对照不同场景的光照与景深 | [六景总览](references/visuals/昼暮夜六景.jpg) · [全部视觉参考](references/visuals/) · [早期六景补光词](references/六景原始补光词.txt) |

## 参考素材

《逸剑风云决》的街市与千陵渡画面用于观察机位、人物尺度和街面层次。《八方旅人Ⅱ》的卡纳尔布来因昼夜画面用于观察景深、窗光和水面反射。图源记录见[千陵渡实况](https://www.bilibili.com/video/BV1413Q6XEWC/?p=37)与[卡纳尔布来因图集](https://octopathtraveler.fandom.com/wiki/Canalbrine)。

宇文逸的原图及透明站姿用于校准 NPC 的像素尺寸。渡口的环境、NPC 和三张成图是工作流示例；游戏截图和人物参考保留各自来源。
