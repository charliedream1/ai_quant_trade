# -*- coding: utf-8 -*-
"""看盘神器 V2 讲解 GIF 生成器

从已渲染的视频帧中抽取精华场景，生成 15 秒左右的 GIF，
用于 GitHub README 展示。

特点：
  - 800px 宽，文件约 3-5 MB
  - 9 个场景精华串烧（每个约 1.7 秒）
  - 15 fps，约 225 帧
  - 无字幕（GIF 体积敏感）
"""
from pathlib import Path
from PIL import Image, ImageSequence

BASE_DIR = Path(__file__).parent
FRAMES_DIR = BASE_DIR / "frames"
OUTPUT_GIF = BASE_DIR / "看盘神器V2演示.gif"

# GIF 参数
TARGET_WIDTH = 480  # 480px 宽，更小体积
FPS = 10            # 10fps，GIF 体积敏感
TOTAL_DURATION_SEC = 15
TOTAL_FRAMES = FPS * TOTAL_DURATION_SEC  # 150 帧

# 场景精华抽取配置
# (scene_id, start_progress, end_progress, frames_count)
# 每个场景抽取精华片段，避开开场淡入和结尾淡出
SCENE_SEGMENTS = [
    (1,  0.30, 0.85, 15),  # 开场宣传：GitHub + 二维码
    (2,  0.50, 0.90, 13),  # 痛点引入：V2 解决方案
    (3,  0.30, 0.85, 17),  # 六大亮点：卡片展开
    (4,  0.55, 0.95, 18),  # 预警监控：触发+弹窗
    (5,  0.40, 0.95, 17),  # K线图：蜡烛绘制
    (6,  0.50, 0.95, 15),  # 资金情绪：仪表盘
    (7,  0.45, 0.95, 15),  # 股票池：搜索结果
    (9,  0.40, 0.85, 18),  # 使用方法：五步
    (11, 0.30, 0.85, 22),  # 结尾宣传：二维码
]


def load_scene_frames(scene_id: int) -> list:
    """加载场景的所有帧"""
    scene_dir = FRAMES_DIR / f"scene_{scene_id:02d}"
    if not scene_dir.exists():
        print(f"  [警告] 场景 {scene_id:02d} 帧目录不存在: {scene_dir}")
        return []
    frames = sorted(scene_dir.glob("frame_*.png"))
    return frames


def extract_segment(frames: list, start_p: float, end_p: float, count: int) -> list:
    """从帧列表中抽取指定进度区间的帧"""
    if not frames:
        return []
    total = len(frames)
    start_idx = int(total * start_p)
    end_idx = int(total * end_p)
    if end_idx <= start_idx:
        end_idx = min(total - 1, start_idx + count)
    # 均匀抽取 count 帧
    if end_idx - start_idx + 1 <= count:
        indices = list(range(start_idx, end_idx + 1))
    else:
        step = (end_idx - start_idx) / (count - 1)
        indices = [int(start_idx + i * step) for i in range(count)]
    indices = [min(i, total - 1) for i in indices]
    return [frames[i] for i in indices]


def resize_frame(img: Image.Image, target_width: int) -> Image.Image:
    """按比例缩放到目标宽度"""
    w, h = img.size
    new_h = int(h * target_width / w)
    # 缩小用 LANCZOS，画质最好
    return img.resize((target_width, new_h), Image.LANCZOS)


def add_scene_label(img: Image.Image, label: str) -> Image.Image:
    """在画面顶部加场景标签（小型，便于 GIF 识别内容）"""
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img, "RGBA")
    # 半透明背景条
    bar_h = 32
    draw.rectangle([0, 0, img.size[0], bar_h], fill=(0, 0, 0, 160))
    # 文字
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 18)
    except Exception:
        font = ImageFont.load_default()
    draw.text((12, 6), label, font=font, fill=(255, 255, 255, 255))
    return img


def generate_gif():
    print("=" * 60)
    print("看盘神器 V2 讲解 GIF 生成器")
    print(f"目标: {TARGET_WIDTH}px 宽, {TOTAL_DURATION_SEC}s, {FPS}fps")
    print("=" * 60)

    # 场景标签
    scene_labels = {
        1: "AI 股票操盘手 · GitHub 5.9k+",
        2: "上班族的痛点",
        3: "V2 六大特色亮点",
        4: "预警监控",
        5: "K线图",
        6: "资金情绪",
        7: "股票池选股",
        9: "五步快速上手",
        11: "立即加入我们",
    }

    all_frames = []
    print("\n=== 抽取场景精华 ===")
    for scene_id, start_p, end_p, count in SCENE_SEGMENTS:
        frames = load_scene_frames(scene_id)
        if not frames:
            continue
        segment = extract_segment(frames, start_p, end_p, count)
        label = scene_labels.get(scene_id, "")
        print(f"  场景 {scene_id:02d} [{label}]: 抽取 {len(segment)} 帧 "
              f"(进度 {start_p:.0%}-{end_p:.0%})")
        for f in segment:
            img = Image.open(f).convert("RGB")
            img = resize_frame(img, TARGET_WIDTH)
            if label:
                img = add_scene_label(img, label)
            all_frames.append(img)

    print(f"\n=== 总帧数: {len(all_frames)} ===")
    if not all_frames:
        print("[错误] 没有帧可生成 GIF")
        return False

    # 帧间隔（毫秒）
    frame_duration = int(1000 / FPS)

    print(f"\n=== 生成 GIF ===")
    print(f"  尺寸: {all_frames[0].size}")
    print(f"  帧数: {len(all_frames)}")
    print(f"  帧间隔: {frame_duration}ms")
    print(f"  总时长: {len(all_frames) * frame_duration / 1000:.1f}s")
    print(f"  输出: {OUTPUT_GIF}")

    # 转换为 P 模式（256 色自适应调色板）大幅减小体积
    # 关键：所有帧共享同一个调色板，避免每帧都存调色板
    print("\n=== 转换为 256 色共享调色板（优化体积）===")

    # 先合成所有帧生成一个全局调色板
    # 用首帧 + 几个关键帧生成调色板
    sample_indices = [0, len(all_frames)//4, len(all_frames)//2, 3*len(all_frames)//4, -1]
    sample_frames = [all_frames[i] for i in sample_indices]
    # 拼接成大图生成调色板
    total_w = sum(f.size[0] for f in sample_frames)
    max_h = max(f.size[1] for f in sample_frames)
    palette_img = Image.new("RGB", (total_w, max_h))
    x = 0
    for f in sample_frames:
        palette_img.paste(f, (x, 0))
        x += f.size[0]
    # 量化生成全局调色板
    palette_img_p = palette_img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    global_palette = palette_img_p.getpalette()

    # 用全局调色板转换所有帧
    converted_frames = []
    for i, frame in enumerate(all_frames):
        p_frame = frame.convert("RGB").quantize(
            colors=256,
            method=Image.Quantize.MEDIANCUT,
            palette=palette_img_p,
        )
        converted_frames.append(p_frame)
        if i == 0:
            print(f"  首帧转换完成: {frame.size} RGB -> P 模式 (共享调色板)")

    # 生成 GIF
    # disposal=2 表示每帧绘制前清除背景，避免残影
    # loop=0 表示无限循环
    converted_frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=converted_frames[1:],
        duration=frame_duration,
        loop=0,
        disposal=2,
        optimize=True,
    )

    size_mb = OUTPUT_GIF.stat().st_size / 1024 / 1024
    print(f"\n✅ GIF 生成完成!")
    print(f"   📁 路径: {OUTPUT_GIF}")
    print(f"   📦 大小: {size_mb:.2f} MB")
    print(f"   ⏱ 时长: {len(all_frames) * frame_duration / 1000:.1f}s")
    print(f"   📐 尺寸: {all_frames[0].size[0]}x{all_frames[0].size[1]}")

    return True


if __name__ == "__main__":
    generate_gif()
