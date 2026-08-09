# -*- coding: utf-8 -*-
"""看盘神器 V2 功能讲解视频生成器（v4 精美优化版）

优化点（相对 v3）：
  1. 修复二维码比例：原图 1050×537 横向长图，按 1.96:1 比例展示，可识别
  2. 恢复精美功能演示：预警监控/K线图/资金情绪/股票池 动画讲解
  3. Excel 截图仅作辅助展示（6 张轮播，1 个场景）
  4. 痛点场景融入 README 精美图片
  5. 保留：开场/结尾宣传、六大亮点、使用方法、多源容错

流程：
  1. edge-tts 生成中文配音
  2. Pillow 渲染带字幕的帧序列
  3. ffmpeg 合成最终 MP4
"""
import asyncio
import os
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# === 路径配置 ===
BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "audio"
FRAMES_DIR = BASE_DIR / "frames"
OUTPUT_MP4 = BASE_DIR / "看盘神器V2讲解视频.mp4"

AUDIO_DIR.mkdir(exist_ok=True)
FRAMES_DIR.mkdir(exist_ok=True)

# === ffmpeg 路径 ===
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# === 字体配置 ===
FONT_TITLE = r"C:\Windows\Fonts\msyhbd.ttc"  # 微软雅黑 Bold
FONT_BODY = r"C:\Windows\Fonts\msyh.ttc"     # 微软雅黑 Regular
FONT_CODE = r"C:\Windows\Fonts\consola.ttf"  # Consolas

# === 视频参数 ===
WIDTH, HEIGHT = 1920, 1080
FPS = 30

# === 配色 ===
BG_COLOR = (15, 23, 42)        # 深蓝黑
PRIMARY = (59, 130, 246)       # 蓝色
ACCENT = (16, 185, 129)        # 绿色
WARNING = (245, 158, 11)       # 橙色
DANGER = (220, 60, 60)         # 红色
TEXT_MAIN = (241, 245, 249)    # 浅灰白
TEXT_DIM = (148, 163, 184)     # 灰
CARD_BG = (30, 41, 59)         # 卡片背景
GITHUB_BG = (36, 41, 46)       # GitHub 深色
UP_COLOR = (220, 60, 60)       # A股红涨
DOWN_COLOR = (16, 185, 129)    # A股绿跌


# === 分镜脚本（11 个场景，恢复精美讲解） ===
SCENES = [
    # 1. 开场宣传：GitHub + 星球横向二维码
    {
        "id": 1,
        "title": "AI 股票操盘手",
        "narration": "AI 股票操盘手，GitHub 已获 5.9k 以上 Star，开源量化交易辅助工具集。欢迎扫码加入知识星球，获取更多代码与视频资源。",
        "duration": 10.0,
        "type": "promo",
        "repo_url": "github.com/charliedream1/ai_quant_trade",
        "gitee_url": "gitee.com/charlie1/ai_quant_trade",
        "stars": "5.9k+",
        "qrcode": "quant_qrcode.jpg",
        "zsxq_url": "t.zsxq.com/dHt9l",
        "variant": "opening",
    },
    # 2. 痛点引入（融入 README 精美图片）
    {
        "id": 2,
        "title": "上班族的痛点",
        "narration": "作为上班族，又要上班又要炒股，真心累。用手机看盘屏幕太小，错失时机；用电脑看盘又怕被领导发现，像做贼一样，心惊胆战。一不小心错过买卖点，痛心疾首。",
        "duration": 13.0,
        "type": "pain_points",
    },
    # 3. V2 方案 + 六大亮点
    {
        "id": 3,
        "title": "V2 方案：六大特色亮点",
        "narration": "看盘神器 V2 用 Excel 作为看盘界面，伪装成工作表格，超隐蔽。六大特色亮点：预警监控、K线图、Excel配置、多源容错、资金情绪、股票池选股。",
        "duration": 11.0,
        "type": "solution",
        "highlights": [
            ("🔥", "预警监控", "涨跌幅/价格上下限，自动高亮+弹窗", WARNING),
            ("📈", "K线图", "Excel里点按钮就画，带均线", PRIMARY),
            ("⚙", "Excel配置", "自选股、指数、间隔，热生效", ACCENT),
            ("🔄", "多源容错", "主源挂了自动切换5个备选源", PRIMARY),
            ("💰", "资金情绪", "北向+微博+股吧，一屏看全", ACCENT),
            ("🔍", "股票池选股", "全A股模糊搜索+下拉框", WARNING),
        ],
    },
    # 4. 预警监控精美演示
    {
        "id": 4,
        "title": "亮点一：预警监控",
        "narration": "在个性定制看盘 Sheet 设好涨跌幅上下限，股价一旦超过阈值，整行自动变红，并弹出预警弹窗，不错过任何买卖点。",
        "duration": 9.0,
        "type": "alert_demo",
    },
    # 5. K线图精美演示
    {
        "id": 5,
        "title": "亮点二：K线图",
        "narration": "在 Excel 里点个按钮就能画 K 线图，蜡烛图带五日十日均线，不用切软件，看盘分析两不误。",
        "duration": 9.0,
        "type": "kline_demo",
    },
    # 6. 资金情绪精美可视化
    {
        "id": 6,
        "title": "亮点三：资金情绪",
        "narration": "资金情绪 Sheet 一屏看全：北向资金实时流入、微博舆情指数、新闻情绪、股吧热门，多维度把握市场情绪。",
        "duration": 9.0,
        "type": "sentiment_viz",
    },
    # 7. 股票池选股精美演示
    {
        "id": 7,
        "title": "亮点四：股票池选股",
        "narration": "内置全 A 五千多只股票，输入代码、名称或拼音首字母模糊搜索，下拉框直接选，再也不用手动查代码。",
        "duration": 9.0,
        "type": "stock_pool_demo",
    },
    # 8. Excel 实景效果展示（6 张轮播，辅助佐证）
    {
        "id": 8,
        "title": "Excel 实景效果",
        "narration": "下面展示真实 Excel 运行界面：大盘总览、详细行情、财经新闻、个性看盘、资金情绪、股票池，七大 Sheet 开箱即用。",
        "duration": 13.0,
        "type": "excel_showcase",
        "screenshots": [
            ("excel_screenshots/market_overview.png", "大盘总览 Sheet"),
            ("excel_screenshots/detailed_quotes.png", "详细行情 Sheet"),
            ("excel_screenshots/news.png", "财经新闻 Sheet"),
            ("excel_screenshots/custom_watch.png", "个性定制看盘 Sheet"),
            ("excel_screenshots/sentiment.png", "资金情绪 Sheet"),
            ("excel_screenshots/stock_pool.png", "股票池 Sheet"),
        ],
    },
    # 9. 使用方法 5 步
    {
        "id": 9,
        "title": "五步快速上手",
        "narration": "使用方法很简单。第一步，安装依赖。第二步，生成 Excel 模板。第三步，在 Excel 里填写自选股。第四步，启动程序。第五步，想改配置直接在 Excel 里改，热生效，不用重启。",
        "duration": 14.0,
        "type": "usage",
        "steps": [
            ("1", "安装依赖", "pip install -r requirements.txt", PRIMARY),
            ("2", "生成模板", "python main.py --generate-template", ACCENT),
            ("3", "填写自选股", "在详细行情/个性看盘 Sheet 代码列填写", WARNING),
            ("4", "启动程序", "python main.py", PRIMARY),
            ("5", "热改配置", "Excel 配置 Sheet 改完自动生效", ACCENT),
        ],
    },
    # 10. 多源容错（技术亮点）
    {
        "id": 10,
        "title": "六大数据源容错",
        "narration": "内置六大数据源容错机制：qstock、akshare、东方财富、腾讯、网易、baostock，主源失败自动切换，盯盘不中断。",
        "duration": 9.0,
        "type": "fallback_chain",
        "sources": ["qstock", "akshare", "eastmoney", "tencent", "netease", "baostock"],
    },
    # 11. 结尾宣传：仓库 + 横向二维码
    {
        "id": 11,
        "title": "立即加入我们",
        "narration": "AI 股票操盘手，GitHub 5.9k 以上 Star，欢迎 Star 支持。开源代码仓库地址请见画面，更多代码视频资源，扫码加入知识星球。",
        "duration": 11.0,
        "type": "promo",
        "repo_url": "github.com/charliedream1/ai_quant_trade",
        "gitee_url": "gitee.com/charlie1/ai_quant_trade",
        "stars": "5.9k+",
        "qrcode": "quant_qrcode.jpg",
        "zsxq_url": "t.zsxq.com/dHt9l",
        "variant": "ending",
    },
]


# ============================================================
# 工具函数
# ============================================================
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_TITLE if bold else FONT_BODY
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(FONT_BODY, size)


def _draw_rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2


def _draw_text_centered(draw, text, y, font, fill, width=WIDTH):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)


def _draw_text_centered_at(draw, text, cx, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y), text, font=font, fill=fill)


def _draw_text_right_at(draw, text, right_x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((right_x - tw, y), text, font=font, fill=fill)


def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """按比例缩放图片到指定范围"""
    sw, sh = img.size
    scale = min(max_w / sw, max_h / sh)
    return img.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)


# ============================================================
# 渲染器 1：宣传场景（修复二维码横向比例）
# ============================================================
def render_promo_frame(scene: dict, progress: float) -> Image.Image:
    """宣传场景：GitHub 仓库 + Star 数 + 知识星球横向二维码

    二维码原图 1050×537（宽高比 1.96），按原始横向比例展示，保证可识别。
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")
    variant = scene.get("variant", "opening")

    # 顶部装饰条
    draw.rectangle([0, 0, WIDTH, 8], fill=PRIMARY)

    # === 上半部分：仓库信息（居中布局）===
    # 主标题
    title_font = _font(64, bold=True)
    if progress > 0.05:
        alpha = int(255 * min(1, (progress - 0.05) * 4))
        _draw_text_centered(draw, scene["title"], 60, title_font, (*TEXT_MAIN, alpha))

    # GitHub Star 徽章（居中）
    if progress > 0.15:
        alpha = int(255 * min(1, (progress - 0.15) * 4))
        badge_w, badge_h = 360, 64
        badge_x = (WIDTH - badge_w) // 2
        badge_y = 160
        _draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                           12, (*GITHUB_BG, alpha))
        # Star 图标
        draw.ellipse([badge_x + 18, badge_y + 18, badge_x + 46, badge_y + 46],
                     fill=(*WARNING, alpha))
        star_font = _font(26, bold=True)
        draw.text((badge_x + 58, badge_y + 16), "GitHub", font=star_font, fill=(*TEXT_MAIN, alpha))
        # Star 数
        star_count_font = _font(30, bold=True)
        _draw_text_right_at(draw, scene["stars"], badge_x + badge_w - 20, badge_y + 16,
                            star_count_font, (*WARNING, alpha))

    # 仓库地址（居中，双行）
    if progress > 0.25:
        alpha = int(255 * min(1, (progress - 0.25) * 4))
        url_y = 250
        label_font = _font(22)
        url_font = _font(30, bold=True)
        # GitHub
        gh_label = "GitHub 开源仓库："
        gh_url = scene["repo_url"]
        gh_full = gh_label + gh_url
        bbox = draw.textbbox((0, 0), gh_full, font=url_font)
        gh_w = bbox[2] - bbox[0]
        gh_x = (WIDTH - gh_w) // 2
        draw.text((gh_x, url_y), gh_label, font=label_font, fill=(*TEXT_DIM, alpha))
        bbox_l = draw.textbbox((0, 0), gh_label, font=label_font)
        draw.text((gh_x + bbox_l[2] - bbox_l[0], url_y), gh_url, font=url_font, fill=(*PRIMARY, alpha))
        # Gitee
        ge_label = "Gitee 国内镜像："
        ge_url = scene["gitee_url"]
        ge_full = ge_label + ge_url
        bbox = draw.textbbox((0, 0), ge_full, font=url_font)
        ge_w = bbox[2] - bbox[0]
        ge_x = (WIDTH - ge_w) // 2
        draw.text((ge_x, url_y + 42), ge_label, font=label_font, fill=(*TEXT_DIM, alpha))
        draw.text((ge_x + bbox_l[2] - bbox_l[0], url_y + 42), ge_url, font=url_font, fill=(*ACCENT, alpha))

    # === 下半部分：知识星球横向二维码（保持 1.96:1 比例）===
    qrcode_path = BASE_DIR / scene["qrcode"]
    if qrcode_path.exists() and progress > 0.2:
        alpha = int(255 * min(1, (progress - 0.2) * 3))
        try:
            qr = Image.open(qrcode_path).convert("RGBA")
            # 原图 1050×537，宽高比 1.96，按比例放大到 1100×561
            qr_w = 1100
            qr_h = int(qr_w / qr.size[0] * qr.size[1])  # 保持原比例
            qr = qr.resize((qr_w, qr_h), Image.LANCZOS)
            qr_x = (WIDTH - qr_w) // 2
            qr_y = 360

            # 白色背景框（带淡入）
            pad = 16
            _draw_rounded_rect(draw,
                               [qr_x - pad, qr_y - pad, qr_x + qr_w + pad, qr_y + qr_h + pad],
                               16, (255, 255, 255, alpha))
            # 贴二维码（带淡入）
            if alpha < 255:
                qr.putalpha(alpha)
            img.paste(qr, (qr_x, qr_y), qr if alpha < 255 else None)

            draw = ImageDraw.Draw(img, "RGBA")
            # 二维码下方说明
            zsxq_font = _font(28, bold=True)
            _draw_text_centered(draw, f"扫码加入知识星球 · {scene['zsxq_url']}",
                                qr_y + qr_h + 30, zsxq_font, (*ACCENT, alpha))
            desc_font = _font(22)
            _draw_text_centered(draw, "获取更多代码视频资源",
                                qr_y + qr_h + 68, desc_font, (*TEXT_DIM, alpha))
        except Exception as e:
            err_font = _font(28)
            draw.text((100, 500), f"二维码加载失败: {e}", font=err_font, fill=DANGER)

    # 底部装饰条
    draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=PRIMARY)

    return img


# ============================================================
# 渲染器 2：痛点引入（融入 README 精美图片）
# ============================================================
def render_pain_points_frame(scene: dict, progress: float) -> Image.Image:
    """痛点引入：左侧 README 图片 + 右侧痛点卡片"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(52, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 左侧：README 精美图片（2_工作与炒股.png）
    img1_path = BASE_DIR / "readme_images" / "2_工作与炒股.png"
    if img1_path.exists():
        try:
            pic1 = Image.open(img1_path).convert("RGBA")
            pic1 = _fit_image(pic1, 760, 460)
            pw, ph = pic1.size
            px = 80
            py = 150
            # 阴影
            _draw_rounded_rect(draw,
                               [px - 8 + 6, py - 8 + 6, px + pw + 8 + 6, py + ph + 8 + 6],
                               12, (0, 0, 0, 100))
            # 白框
            _draw_rounded_rect(draw,
                               [px - 8, py - 8, px + pw + 8, py + ph + 8],
                               12, (245, 245, 245, 255))
            img.paste(pic1, (px, py))
            draw = ImageDraw.Draw(img, "RGBA")
            # 图片说明
            cap_font = _font(22)
            _draw_text_centered_at(draw, "工作 vs 炒股，两头不能兼顾", px + pw // 2, py + ph + 18,
                                   cap_font, TEXT_DIM)
        except Exception:
            pass

    # 右侧：README 图片（1_有点慌.png）
    img2_path = BASE_DIR / "readme_images" / "1_有点慌.png"
    if img2_path.exists() and progress > 0.3:
        try:
            alpha = int(255 * min(1, (progress - 0.3) * 3))
            pic2 = Image.open(img2_path).convert("RGBA")
            pic2 = _fit_image(pic2, 760, 460)
            pw, ph = pic2.size
            px = WIDTH - 80 - pw
            py = 150
            _draw_rounded_rect(draw,
                               [px - 8 + 6, py - 8 + 6, px + pw + 8 + 6, py + ph + 8 + 6],
                               12, (0, 0, 0, 100))
            _draw_rounded_rect(draw,
                               [px - 8, py - 8, px + pw + 8, py + ph + 8],
                               12, (245, 245, 245, alpha))
            if alpha < 255:
                pic2.putalpha(alpha)
            img.paste(pic2, (px, py), pic2 if alpha < 255 else None)
            draw = ImageDraw.Draw(img, "RGBA")
            cap_font = _font(22)
            _draw_text_centered_at(draw, "悄悄看盘，吓得心扑通跳", px + pw // 2, py + ph + 18,
                                   cap_font, (*TEXT_DIM, alpha))
        except Exception:
            pass

    # 底部 V2 解决方案
    if progress > 0.6:
        alpha = int(255 * min(1, (progress - 0.6) * 2.5))
        sol_y = 720
        _draw_rounded_rect(draw, [200, sol_y, WIDTH - 200, sol_y + 200], 16, (20, 50, 40, alpha))
        draw.rectangle([200, sol_y, 224, sol_y + 200], fill=(*ACCENT, alpha))

        sol_font = _font(40, bold=True)
        _draw_text_centered(draw, "V2 解决方案：用 Excel 作为看盘界面", sol_y + 35, sol_font, (*ACCENT, alpha))
        sol_desc_font = _font(28)
        _draw_text_centered(draw, "伪装成工作表格，超隐蔽 · 领导路过也不怕", sol_y + 95, sol_desc_font, (*TEXT_MAIN, alpha))
        sol_desc2_font = _font(24)
        _draw_text_centered(draw, "七大 Sheet 一屏看全 · 预警监控 · K线图 · 热配置",
                            sol_y + 140, sol_desc2_font, (*TEXT_DIM, alpha))

    return img


# ============================================================
# 渲染器 3：V2 方案 + 六大亮点
# ============================================================
def render_solution_frame(scene: dict, progress: float) -> Image.Image:
    """V2 方案 + 六大特色亮点（2x3 网格）"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(52, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 2行3列网格
    highlights = scene["highlights"]
    cols, rows = 3, 2
    card_w, card_h = 540, 340
    gap_x, gap_y = 40, 30
    total_w = cols * card_w + (cols - 1) * gap_x
    start_x = (WIDTH - total_w) // 2
    start_y = 140

    for i, (emoji, name, desc, color) in enumerate(highlights):
        col = i % cols
        row = i // cols
        x = start_x + col * (card_w + gap_x)
        y = start_y + row * (card_h + gap_y)

        cp = max(0, min(1, (progress - i * 0.1) / 0.5))
        if cp <= 0:
            continue
        eased = _ease_in_out(cp)
        offset_y = int((1 - eased) * 40)
        alpha = int(255 * eased)

        _draw_rounded_rect(draw, [x, y + offset_y, x + card_w, y + card_h + offset_y],
                           16, (*CARD_BG, alpha))
        draw.rectangle([x, y + offset_y, x + 8, y + card_h + offset_y], fill=(*color, alpha))

        emoji_font = _font(56, bold=True)
        draw.text((x + 40, y + 30 + offset_y), emoji, font=emoji_font, fill=(*TEXT_MAIN, alpha))
        name_font = _font(36, bold=True)
        draw.text((x + 120, y + 50 + offset_y), name, font=name_font, fill=(*color, alpha))
        desc_font = _font(24)
        # 简单换行
        if len(desc) > 18:
            mid = len(desc) // 2
            for off in range(10):
                if desc[mid + off] in "，。、 ":
                    line1 = desc[:mid + off + 1]
                    line2 = desc[mid + off + 1:]
                    break
            else:
                line1, line2 = desc[:mid], desc[mid:]
            draw.text((x + 40, y + 170 + offset_y), line1, font=desc_font, fill=(*TEXT_MAIN, alpha))
            draw.text((x + 40, y + 210 + offset_y), line2, font=desc_font, fill=(*TEXT_DIM, alpha))
        else:
            draw.text((x + 40, y + 180 + offset_y), desc, font=desc_font, fill=(*TEXT_MAIN, alpha))

    # 底部小字
    if progress > 0.8:
        alpha = int(255 * min(1, (progress - 0.8) * 5))
        foot_font = _font(24)
        _draw_text_centered(draw, "相比 V1 彻底重构 · 模块化架构 · 156 项单元测试",
                           HEIGHT - 60, foot_font, (*TEXT_DIM, alpha))

    return img


# ============================================================
# 渲染器 4：预警监控精美演示（动画）
# ============================================================
def render_alert_demo_frame(scene: dict, progress: float) -> Image.Image:
    """预警监控：模拟 Excel 表格行，股价跳动，超阈值整行变红 + 弹窗"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(48, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 模拟表格
    table_x, table_y = 200, 140
    table_w = WIDTH - 400
    row_h = 56
    headers = ["代码", "名称", "最新价", "涨跌幅", "预警上限", "预警下限", "状态"]
    col_widths = [180, 200, 160, 160, 160, 160, 200]
    stocks = [
        ("600519", "贵州茅台", 1685.00, 2.3, 3.0, -2.0, "监控中"),
        ("000001", "平安银行", 12.45, 5.8, 3.0, -2.0, "⚠ 触发"),
        ("601318", "中国平安", 48.20, -1.2, 3.0, -2.0, "监控中"),
        ("000858", "五粮液", 156.80, 3.5, 3.0, -2.0, "⚠ 触发"),
        ("002594", "比亚迪", 245.60, 0.8, 3.0, -2.0, "监控中"),
    ]

    # 表头
    header_font = _font(24, bold=True)
    _draw_rounded_rect(draw, [table_x, table_y, table_x + table_w, table_y + row_h],
                       8, (*PRIMARY, 255))
    cx = table_x + 16
    for i, (h, cw) in enumerate(zip(headers, col_widths)):
        draw.text((cx, table_y + 14), h, font=header_font, fill=(255, 255, 255, 255))
        cx += cw

    # 数据行
    cell_font = _font(22)
    for ri, (code, name, price, chg, hi, lo, status) in enumerate(stocks):
        ry = table_y + (ri + 1) * row_h
        # 行背景
        row_bg = CARD_BG
        row_alpha = 255
        # 判断是否触发预警（涨跌幅超过上限）
        triggered = abs(chg) > hi
        # 触发时机：每只股票在不同 progress 触发
        trigger_progress = 0.3 + ri * 0.12
        is_triggered = triggered and progress > trigger_progress

        if is_triggered:
            # 整行变红（闪烁效果）
            flash = 0.7 + 0.3 * abs((progress * 10) % 2 - 1)
            row_bg = (int(220 * flash), int(60 * flash), int(60 * flash))
            row_alpha = int(220 * flash)

        _draw_rounded_rect(draw, [table_x, ry, table_x + table_w, ry + row_h],
                           4, (*row_bg, row_alpha))

        # 价格动画：随 progress 微微跳动
        price_offset = int((progress * 10 + ri) % 5) - 2
        animated_price = price + price_offset * 0.01 * price
        chg_offset = (progress * 5 + ri) % 3 - 1
        animated_chg = chg + chg_offset * 0.3

        cx = table_x + 16
        values = [code, name, f"{animated_price:.2f}", f"{animated_chg:+.1f}%",
                  f"{hi:.1f}%", f"{lo:.1f}%", status]
        for i, (v, cw) in enumerate(zip(values, col_widths)):
            color = TEXT_MAIN
            if i == 3:  # 涨跌幅列
                color = UP_COLOR if animated_chg > 0 else DOWN_COLOR
            if i == 6 and is_triggered:  # 状态列
                color = WARNING
            draw.text((cx, ry + 16), v, font=cell_font, fill=(*color, 255))
            cx += cw

    # 预警弹窗（progress > 0.6 时出现）
    if progress > 0.6:
        pop_alpha = int(255 * min(1, (progress - 0.6) * 3))
        pop_w, pop_h = 560, 200
        pop_x = (WIDTH - pop_w) // 2
        pop_y = HEIGHT - pop_h - 80
        # 弹窗背景
        _draw_rounded_rect(draw, [pop_x, pop_y, pop_x + pop_w, pop_y + pop_h],
                           16, (*GITHUB_BG, pop_alpha))
        # 红色顶部条
        draw.rectangle([pop_x, pop_y, pop_x + pop_w, pop_y + 8], fill=(*DANGER, pop_alpha))
        # 弹窗内容
        pop_title_font = _font(32, bold=True)
        draw.text((pop_x + 30, pop_y + 30), "⚠ 预警触发", font=pop_title_font, fill=(*WARNING, pop_alpha))
        pop_body_font = _font(26)
        draw.text((pop_x + 30, pop_y + 80), "平安银行(000001) 涨跌幅 5.8% 超过上限 3.0%",
                  font=pop_body_font, fill=(*TEXT_MAIN, pop_alpha))
        draw.text((pop_x + 30, pop_y + 120), "五粮液(000858) 涨跌幅 3.5% 超过上限 3.0%",
                  font=pop_body_font, fill=(*TEXT_MAIN, pop_alpha))
        draw.text((pop_x + 30, pop_y + 160), "请及时关注买卖点",
                  font=_font(22), fill=(*TEXT_DIM, pop_alpha))

    return img


# ============================================================
# 渲染器 5：K线图精美演示（动画绘制）
# ============================================================
def render_kline_demo_frame(scene: dict, progress: float) -> Image.Image:
    """K线图：逐步绘制蜡烛图 + 均线"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(48, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 模拟 K 线数据（OHLC）
    import random
    random.seed(42)
    klines = []
    base_price = 100.0
    for i in range(30):
        open_p = base_price
        change = random.uniform(-3, 3)
        close_p = open_p + change
        high_p = max(open_p, close_p) + random.uniform(0, 2)
        low_p = min(open_p, close_p) - random.uniform(0, 2)
        klines.append((open_p, high_p, low_p, close_p))
        base_price = close_p

    # 图表区域
    chart_x, chart_y = 150, 140
    chart_w = WIDTH - 300
    chart_h = 700

    # 价格范围
    all_prices = [p for k in klines for p in [k[1], k[2]]]
    min_p = min(all_prices) - 2
    max_p = max(all_prices) + 2
    price_range = max_p - min_p

    # 坐标轴背景
    _draw_rounded_rect(draw, [chart_x, chart_y, chart_x + chart_w, chart_y + chart_h],
                       8, (20, 26, 40, 255))

    # 网格线
    for i in range(5):
        gy = chart_y + chart_h * (i + 1) // 6
        draw.line([chart_x + 50, gy, chart_x + chart_w - 20, gy],
                  fill=(40, 50, 70, 255), width=1)
        # 价格标签
        price = max_p - price_range * i / 5
        draw.text((chart_x + 10, gy - 12), f"{price:.0f}", font=_font(18), fill=(*TEXT_DIM, 255))

    # 逐步绘制 K 线（随 progress）
    visible_count = int(len(klines) * min(1, progress * 1.2))
    candle_area_x = chart_x + 50
    candle_area_w = chart_w - 70
    candle_w = candle_area_w / len(klines)
    body_w = candle_w * 0.6

    closes = []
    for i in range(visible_count):
        o, h, l, c = klines[i]
        cx = candle_area_x + i * candle_w + candle_w / 2
        # 价格转坐标
        def to_y(p):
            return chart_y + chart_h - (p - min_p) / price_range * (chart_h - 40) - 20

        # 影线
        color = UP_COLOR if c >= o else DOWN_COLOR
        draw.line([cx, to_y(h), cx, to_y(l)], fill=(*color, 255), width=2)
        # 实体
        body_top = to_y(max(o, c))
        body_bot = to_y(min(o, c))
        body_h = max(2, body_bot - body_top)
        draw.rectangle([cx - body_w / 2, body_top, cx + body_w / 2, body_bot],
                       fill=(*color, 255))
        closes.append(c)

    # 绘制均线（MA5）
    if len(closes) >= 5 and progress > 0.5:
        ma_alpha = int(255 * min(1, (progress - 0.5) * 3))
        ma_points = []
        for i in range(4, len(closes)):
            ma5 = sum(closes[i - 4:i + 1]) / 5
            cx = candle_area_x + i * candle_w + candle_w / 2
            ma_points.append((cx, to_y(ma5)))
        if len(ma_points) > 1:
            draw.line(ma_points, fill=(*WARNING, ma_alpha), width=3)

    # 图例
    if progress > 0.6:
        leg_alpha = int(255 * min(1, (progress - 0.6) * 3))
        leg_font = _font(22)
        # 红涨
        draw.rectangle([chart_x + chart_w - 280, chart_y + 20,
                        chart_x + chart_w - 260, chart_y + 40], fill=(*UP_COLOR, leg_alpha))
        draw.text((chart_x + chart_w - 250, chart_y + 22), "上涨", font=leg_font, fill=(*TEXT_MAIN, leg_alpha))
        # 绿跌
        draw.rectangle([chart_x + chart_w - 180, chart_y + 20,
                        chart_x + chart_w - 160, chart_y + 40], fill=(*DOWN_COLOR, leg_alpha))
        draw.text((chart_x + chart_w - 150, chart_y + 22), "下跌", font=leg_font, fill=(*TEXT_MAIN, leg_alpha))
        # MA5
        draw.line([chart_x + chart_w - 90, chart_y + 30,
                   chart_x + chart_w - 70, chart_y + 30], fill=(*WARNING, leg_alpha), width=3)
        draw.text((chart_x + chart_w - 60, chart_y + 22), "MA5", font=leg_font, fill=(*TEXT_MAIN, leg_alpha))

    # 底部说明
    if progress > 0.7:
        alpha = int(255 * min(1, (progress - 0.7) * 3))
        tip_font = _font(24)
        _draw_text_centered(draw, "Excel 里点按钮即可绘制 · mplfinance 蜡烛图 · 支持均线",
                           HEIGHT - 60, tip_font, (*ACCENT, alpha))

    return img


# ============================================================
# 渲染器 6：资金情绪精美可视化（仪表盘）
# ============================================================
def render_sentiment_viz_frame(scene: dict, progress: float) -> Image.Image:
    """资金情绪：北向资金条形图 + 舆情仪表盘 + 新闻情绪"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(48, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 三个区块
    block_y = 140
    block_h = 760

    # === 左：北向资金条形图 ===
    if progress > 0.1:
        alpha = int(255 * min(1, (progress - 0.1) * 3))
        bx, bw = 80, 560
        _draw_rounded_rect(draw, [bx, block_y, bx + bw, block_y + block_h], 12, (*CARD_BG, alpha))
        draw.rectangle([bx, block_y, bx + 8, block_y + block_h], fill=(*PRIMARY, alpha))
        title_f = _font(30, bold=True)
        draw.text((bx + 30, block_y + 20), "北向资金", font=title_f, fill=(*PRIMARY, alpha))

        # 条形图
        data = [("沪股通", 85.6, UP_COLOR), ("深股通", -32.4, DOWN_COLOR), ("合计", 53.2, UP_COLOR)]
        bar_x = bx + 60
        bar_w_max = 320
        bar_h = 50
        bar_y0 = block_y + 100
        for i, (name, val, color) in enumerate(data):
            by = bar_y0 + i * 100
            draw.text((bar_x, by - 35), name, font=_font(22), fill=(*TEXT_MAIN, alpha))
            # 0 轴
            axis_x = bar_x + bar_w_max // 2
            draw.line([axis_x, by, axis_x, by + bar_h], fill=(*TEXT_DIM, alpha), width=2)
            # 条
            bar_len = int(abs(val) / 100 * bar_w_max / 2 * min(1, max(0, (progress - 0.2 - i * 0.1) * 3)))
            if val >= 0:
                draw.rectangle([axis_x, by + 10, axis_x + bar_len, by + bar_h - 10], fill=(*color, alpha))
            else:
                draw.rectangle([axis_x - bar_len, by + 10, axis_x, by + bar_h - 10], fill=(*color, alpha))
            # 数值
            val_font = _font(24, bold=True)
            val_text = f"{val:+.1f}亿"
            draw.text((bar_x + bar_w_max + 20, by + 12), val_text, font=val_font, fill=(*color, alpha))

    # === 中：微博舆情仪表盘 ===
    if progress > 0.3:
        alpha = int(255 * min(1, (progress - 0.3) * 3))
        bx, bw = 680, 560
        _draw_rounded_rect(draw, [bx, block_y, bx + bw, block_y + block_h], 12, (*CARD_BG, alpha))
        draw.rectangle([bx, block_y, bx + 8, block_y + block_h], fill=(*ACCENT, alpha))
        title_f = _font(30, bold=True)
        draw.text((bx + 30, block_y + 20), "微博舆情指数", font=title_f, fill=(*ACCENT, alpha))

        # 半圆仪表盘
        cx = bx + bw // 2
        cy = block_y + 360
        radius = 180
        # 背景半圆
        draw.pieslice([cx - radius, cy - radius, cx + radius, cy + radius],
                      180, 360, fill=(40, 50, 70, alpha))
        # 数值（0-100，当前 72）
        value = 72
        angle = 180 + int(180 * value / 100 * min(1, max(0, (progress - 0.4) * 4)))
        # 仪表颜色（绿→黄→红）
        if value < 40:
            g_color = ACCENT
        elif value < 70:
            g_color = WARNING
        else:
            g_color = UP_COLOR
        draw.pieslice([cx - radius, cy - radius, cx + radius, cy + radius],
                      180, angle, fill=(*g_color, alpha))
        # 中心圆
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], fill=(*CARD_BG, alpha))
        # 数值文字
        val_f = _font(60, bold=True)
        _draw_text_centered_at(draw, str(value), cx, cy - 40, val_f, (*g_color, alpha))
        _draw_text_centered_at(draw, "偏多", cx, cy + 30, _font(26), (*TEXT_MAIN, alpha))

        # 标签
        _draw_text_centered_at(draw, "散户情绪", cx, cy + radius + 20, _font(22), (*TEXT_DIM, alpha))

    # === 右：新闻情绪 + 股吧热门 ===
    if progress > 0.5:
        alpha = int(255 * min(1, (progress - 0.5) * 3))
        bx, bw = 1280, 560
        _draw_rounded_rect(draw, [bx, block_y, bx + bw, block_y + block_h], 12, (*CARD_BG, alpha))
        draw.rectangle([bx, block_y, bx + 8, block_y + block_h], fill=(*WARNING, alpha))
        title_f = _font(30, bold=True)
        draw.text((bx + 30, block_y + 20), "新闻情绪 & 股吧热门", font=title_f, fill=(*WARNING, alpha))

        # 新闻情绪指数
        draw.text((bx + 30, block_y + 80), "新闻情绪指数", font=_font(24), fill=(*TEXT_MAIN, alpha))
        news_val = 65
        # 进度条
        bar_x = bx + 30
        bar_y = block_y + 120
        bar_w = bw - 60
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 24], fill=(40, 50, 70, alpha))
        fill_w = int(bar_w * news_val / 100 * min(1, max(0, (progress - 0.55) * 5)))
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 24], fill=(*WARNING, alpha))
        draw.text((bar_x + bar_w + 10, bar_y - 4), f"{news_val}", font=_font(22, bold=True), fill=(*WARNING, alpha))

        # 股吧热门
        draw.text((bx + 30, block_y + 180), "股吧热门帖子", font=_font(24), fill=(*TEXT_MAIN, alpha))
        posts = [
            ("贵州茅台", "三季报超预期，目标价2000", 1234),
            ("比亚迪", "新能源销量再创新高", 986),
            ("平安银行", "外资持续流入，看好", 752),
            ("中国平安", "回购计划提振信心", 643),
        ]
        for i, (stock, title, hot) in enumerate(posts):
            py = block_y + 230 + i * 90
            pa = int(255 * min(1, max(0, (progress - 0.6 - i * 0.05) * 4)))
            if pa <= 0:
                continue
            _draw_rounded_rect(draw, [bx + 20, py, bx + bw - 20, py + 78], 6, (40, 50, 70, pa))
            draw.text((bx + 30, py + 10), stock, font=_font(22, bold=True), fill=(*PRIMARY, pa))
            draw.text((bx + 130, py + 12), title, font=_font(20), fill=(*TEXT_MAIN, pa))
            draw.text((bx + 30, py + 44), f"🔥 {hot}", font=_font(18), fill=(*WARNING, pa))

    return img


# ============================================================
# 渲染器 7：股票池选股精美演示（搜索动画）
# ============================================================
def render_stock_pool_demo_frame(scene: dict, progress: float) -> Image.Image:
    """股票池选股：搜索框输入"平安"→结果列表→下拉框"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(48, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 搜索框
    search_x, search_y = 300, 140
    search_w, search_h = WIDTH - 600, 70
    _draw_rounded_rect(draw, [search_x, search_y, search_x + search_w, search_y + search_h],
                       12, (*CARD_BG, 255))
    draw.rectangle([search_x, search_y, search_x + 8, search_y + search_h], fill=(*PRIMARY, 255))

    # 搜索图标
    draw.ellipse([search_x + 25, search_y + 22, search_x + 45, search_y + 42],
                 outline=(*PRIMARY, 255), width=3)
    draw.line([search_x + 42, search_y + 40, search_x + 55, search_y + 53],
              fill=(*PRIMARY, 255), width=3)

    # 输入文字（逐字出现）
    full_keyword = "平安"
    char_count = int(len(full_keyword) * min(1, progress * 3))
    typed = full_keyword[:char_count]
    input_font = _font(32, bold=True)
    draw.text((search_x + 80, search_y + 18), typed, font=input_font, fill=(*TEXT_MAIN, 255))
    # 光标闪烁
    if int(progress * 10) % 2 == 0 and char_count < len(full_keyword):
        bbox = draw.textbbox((0, 0), typed, font=input_font)
        draw.line([search_x + 80 + bbox[2] - bbox[0] + 5, search_y + 22,
                   search_x + 80 + bbox[2] - bbox[0] + 5, search_y + 52],
                  fill=(*PRIMARY, 255), width=2)

    # 搜索提示
    hint_font = _font(22)
    _draw_text_centered(draw, "支持代码 / 名称 / 拼音首字母模糊搜索",
                       search_y + search_h + 15, hint_font, TEXT_DIM)

    # 搜索结果（progress > 0.35 出现）
    if progress > 0.35:
        res_alpha = int(255 * min(1, (progress - 0.35) * 4))
        results = [
            ("000001", "平安银行", "深圳"),
            ("601318", "中国平安", "上海"),
            ("002594", "比亚迪", "深圳"),
        ]
        result_y = search_y + search_h + 70
        result_h = 80
        # 结果标题
        res_title_font = _font(26, bold=True)
        draw.text((search_x, result_y), f"找到 {len(results)} 只匹配股票",
                  font=res_title_font, fill=(*ACCENT, res_alpha))

        headers = ["代码", "名称", "市场"]
        col_x = [search_x, search_x + 300, search_x + 600]
        for i, (code, name, market) in enumerate(results):
            ry = result_y + 50 + i * (result_h + 12)
            ra = int(255 * min(1, max(0, (progress - 0.4 - i * 0.08) * 4)))
            if ra <= 0:
                continue
            _draw_rounded_rect(draw, [search_x, ry, search_x + search_w, ry + result_h],
                               8, (*CARD_BG, ra))
            draw.rectangle([search_x, ry, search_x + 8, ry + result_h], fill=(*ACCENT, ra))
            draw.text((col_x[0] + 20, ry + 25), code, font=_font(28, bold=True), fill=(*PRIMARY, ra))
            draw.text((col_x[1] + 20, ry + 25), name, font=_font(28, bold=True), fill=(*TEXT_MAIN, ra))
            draw.text((col_x[2] + 20, ry + 28), market, font=_font(24), fill=(*TEXT_DIM, ra))

    # 下拉框演示（progress > 0.7）
    if progress > 0.7:
        drop_alpha = int(255 * min(1, (progress - 0.7) * 4))
        drop_x = WIDTH - 480
        drop_y = 140
        drop_w, drop_h = 380, 70
        # 下拉框
        _draw_rounded_rect(draw, [drop_x, drop_y, drop_x + drop_w, drop_y + drop_h],
                           8, (*CARD_BG, drop_alpha))
        draw.rectangle([drop_x, drop_y, drop_x + 8, drop_y + drop_h], fill=(*WARNING, drop_alpha))
        draw.text((drop_x + 25, drop_y + 18), "▼ 点击下拉框选股", font=_font(26, bold=True),
                  fill=(*WARNING, drop_alpha))
        # 下拉箭头
        arrow_font = _font(24)
        draw.text((drop_x + drop_w - 50, drop_y + 22), "▼", font=arrow_font, fill=(*TEXT_DIM, drop_alpha))

        # 下拉选项
        options = ["平安银行 000001", "中国平安 601318", "比亚迪 002594"]
        for i, opt in enumerate(options):
            oy = drop_y + drop_h + 10 + i * 60
            oa = int(255 * min(1, max(0, (progress - 0.75 - i * 0.05) * 5)))
            if oa <= 0:
                continue
            _draw_rounded_rect(draw, [drop_x, oy, drop_x + drop_w, oy + 56],
                               6, (50, 60, 80, oa))
            draw.text((drop_x + 25, oy + 14), opt, font=_font(24), fill=(*TEXT_MAIN, oa))

    return img


# ============================================================
# 渲染器 8：Excel 实景效果展示（6 张轮播）
# ============================================================
def render_excel_showcase_frame(scene: dict, progress: float) -> Image.Image:
    """6 张 Excel 截图轮播展示（带过渡效果）"""
    screenshots = scene["screenshots"]
    # 每 1/6 时段切换一张
    idx = min(len(screenshots) - 1, int(progress * len(screenshots)))
    shot_path, caption = screenshots[idx]

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(44, bold=True)
    _draw_text_centered(draw, scene["title"], 30, title_font, TEXT_MAIN)

    # 索引指示器
    ind_font = _font(24)
    ind_text = f"{idx + 1} / {len(screenshots)}"
    _draw_text_centered(draw, ind_text, 85, ind_font, TEXT_DIM)

    # 加载截图
    full_path = BASE_DIR / shot_path
    if not full_path.exists():
        err_font = _font(36, bold=True)
        _draw_text_centered(draw, f"[截图缺失] {shot_path}", 480, err_font, WARNING)
        return img

    shot = Image.open(full_path).convert("RGB")
    # 适配尺寸
    margin_x = 120
    margin_top = 130
    margin_bottom = 180
    max_w = WIDTH - 2 * margin_x
    max_h = HEIGHT - margin_top - margin_bottom
    shot = _fit_image(shot, max_w, max_h)
    sw, sh = shot.size

    # 过渡淡入效果（每张图前 15% 时段淡入）
    seg_progress = (progress * len(screenshots)) % 1
    fade_alpha = 255
    if seg_progress < 0.15:
        fade_alpha = int(255 * seg_progress / 0.15)

    paste_x = (WIDTH - sw) // 2
    paste_y = margin_top + (max_h - sh) // 2

    # 阴影
    shadow_offset = 8
    _draw_rounded_rect(draw,
                       [paste_x - 8 + shadow_offset, paste_y - 8 + shadow_offset,
                        paste_x + sw + 8 + shadow_offset, paste_y + sh + 8 + shadow_offset],
                       12, (0, 0, 0, 100))
    # 白色相框
    _draw_rounded_rect(draw,
                       [paste_x - 8, paste_y - 8, paste_x + sw + 8, paste_y + sh + 8],
                       12, (245, 245, 245, 255))
    if fade_alpha < 255:
        shot_rgba = shot.convert("RGBA")
        shot_rgba.putalpha(fade_alpha)
        img.paste(shot_rgba, (paste_x, paste_y), shot_rgba)
    else:
        img.paste(shot, (paste_x, paste_y))

    draw = ImageDraw.Draw(img, "RGBA")

    # 底部 caption
    cap_font = _font(30, bold=True)
    _draw_text_centered(draw, caption, HEIGHT - 110, cap_font, (*PRIMARY, 255))

    # 顶部 LIVE 标签
    tag_font = _font(22, bold=True)
    tag_w, tag_h = 130, 36
    tag_x = 60
    tag_y = 30
    draw.rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + tag_h], fill=(220, 60, 60, 255))
    if int(progress * 10) % 2 == 0:
        draw.ellipse([tag_x + 12, tag_y + 12, tag_x + 24, tag_y + 24], fill=(255, 255, 255, 255))
    draw.text((tag_x + 35, tag_y + 7), "LIVE", font=tag_font, fill=(255, 255, 255, 255))

    # 进度条
    bar_x, bar_y = 200, HEIGHT - 50
    bar_w = WIDTH - 400
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 8], fill=(40, 50, 70, 255))
    fill_w = int(bar_w * progress)
    draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 8], fill=(*ACCENT, 255))

    return img


# ============================================================
# 渲染器 9：使用方法 5 步
# ============================================================
def render_usage_frame(scene: dict, progress: float) -> Image.Image:
    """五步快速上手"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(52, bold=True)
    _draw_text_centered(draw, scene["title"], 40, title_font, TEXT_MAIN)

    # 5 个步骤（垂直列表）
    steps = scene["steps"]
    step_h = 130
    step_gap = 15
    list_x = 200
    list_w = WIDTH - 400
    start_y = 140

    for i, (num, name, cmd, color) in enumerate(steps):
        sp = max(0, min(1, (progress - i * 0.12) / 0.4))
        if sp <= 0:
            continue
        eased = _ease_in_out(sp)
        offset_x = int((1 - eased) * 80)
        alpha = int(255 * eased)

        y = start_y + i * (step_h + step_gap)
        x = list_x - offset_x

        # 步骤背景
        _draw_rounded_rect(draw, [x, y, x + list_w, y + step_h], 12, (*CARD_BG, alpha))
        # 左侧色条
        draw.rectangle([x, y, x + 8, y + step_h], fill=(*color, alpha))

        # 步骤号圆圈
        circle_r = 35
        cx, cy = x + 60, y + step_h // 2
        draw.ellipse([cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
                     fill=(*color, alpha))
        num_font = _font(34, bold=True)
        bbox = draw.textbbox((0, 0), num, font=num_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 5), num, font=num_font, fill=(255, 255, 255, alpha))

        # 步骤名
        name_font = _font(34, bold=True)
        draw.text((x + 130, y + 25), name, font=name_font, fill=(*TEXT_MAIN, alpha))
        # 命令/说明（代码字体风格）
        cmd_font = _font(24)
        draw.text((x + 130, y + 75), cmd, font=cmd_font, fill=(*ACCENT, alpha))

    # 底部提示
    if progress > 0.8:
        alpha = int(255 * min(1, (progress - 0.8) * 5))
        tip_font = _font(26)
        _draw_text_centered(draw, "💡 知识星球成员可获取更详细的部署文档与视频教程",
                           HEIGHT - 60, tip_font, (*WARNING, alpha))

    return img


# ============================================================
# 渲染器 10：六大数据源容错链
# ============================================================
def render_fallback_chain_frame(scene: dict, progress: float) -> Image.Image:
    """数据源容错链展示"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 标题
    title_font = _font(52, bold=True)
    _draw_text_centered(draw, scene["title"], 60, title_font, TEXT_MAIN)

    # 容错链
    sources = scene["sources"]
    chain_y = 320
    node_w = 240
    node_h = 100
    gap = 50
    total_w = len(sources) * node_w + (len(sources) - 1) * gap
    start_x = (WIDTH - total_w) // 2

    statuses = ["fail", "fail", "fail", "fail", "fail", "success"]

    for i, (src, status) in enumerate(zip(sources, statuses)):
        np = max(0, min(1, (progress - i * 0.13) / 0.5))
        if np <= 0:
            continue
        eased = _ease_in_out(np)
        alpha = int(255 * eased)

        x = start_x + i * (node_w + gap)
        y = chain_y
        if status == "success":
            color = ACCENT
            label = "✓ 成功"
        else:
            color = DANGER
            label = "✗ 失败"
        _draw_rounded_rect(draw, [x, y, x + node_w, y + node_h], 12, (*CARD_BG, alpha))
        draw.rectangle([x, y, x + node_w, y + 6], fill=(*color, alpha))
        src_font = _font(30, bold=True)
        _draw_text_centered_at(draw, src, x + node_w // 2, y + 25, src_font, (*TEXT_MAIN, alpha))
        status_font = _font(22)
        _draw_text_centered_at(draw, label, x + node_w // 2, y + 68, status_font, (*color, alpha))

        # 箭头
        if i < len(sources) - 1:
            ap = max(0, min(1, (progress - i * 0.13 - 0.3) / 0.3))
            if ap > 0:
                ax = x + node_w
                ay = y + node_h // 2
                aw = int(gap * ap)
                draw.rectangle([ax, ay - 3, ax + aw, ay + 3], fill=(*TEXT_DIM, int(255 * ap)))
                if aw >= gap - 10:
                    draw.polygon([(ax + gap - 5, ay - 10), (ax + gap + 5, ay), (ax + gap - 5, ay + 10)],
                                 fill=(*TEXT_DIM, alpha))

    # 底部说明
    desc_y = 560
    desc_font = _font(30)
    _draw_text_centered(draw, "主数据源失败时，自动按顺序切换到下一个备选源", desc_y, desc_font, TEXT_DIM)

    # 高亮成功节点
    if progress > 0.9:
        sx = start_x + 5 * (node_w + gap)
        _draw_rounded_rect(draw, [sx - 10, chain_y - 10, sx + node_w + 10, chain_y + node_h + 10],
                           16, (20, 60, 40, 200))

    stat_y = 700
    stat_font = _font(38, bold=True)
    _draw_text_centered(draw, "智能容错，数据不中断", stat_y, stat_font, ACCENT)

    return img


# ============================================================
# 字幕叠加
# ============================================================
def render_subtitle_overlay(img: Image.Image, subtitle: str, progress: float) -> Image.Image:
    """在画面底部叠加字幕"""
    draw = ImageDraw.Draw(img, "RGBA")
    if not subtitle:
        return img

    sub_h = 100
    sub_y = HEIGHT - sub_h - 20
    _draw_rounded_rect(draw, [100, sub_y, WIDTH - 100, sub_y + sub_h], 12, (0, 0, 0, 180))

    sub_font = _font(32)
    max_chars = 35
    if len(subtitle) > max_chars:
        mid = len(subtitle) // 2
        for offset in range(20):
            if subtitle[mid + offset] in "，。、 ":
                line1 = subtitle[:mid + offset + 1]
                line2 = subtitle[mid + offset + 1:]
                break
            if subtitle[mid - offset] in "，。、 ":
                line1 = subtitle[:mid - offset + 1]
                line2 = subtitle[mid - offset + 1:]
                break
        else:
            line1, line2 = subtitle[:max_chars], subtitle[max_chars:]
        _draw_text_centered(draw, line1, sub_y + 15, sub_font, TEXT_MAIN)
        _draw_text_centered(draw, line2, sub_y + 55, sub_font, TEXT_MAIN)
    else:
        _draw_text_centered(draw, subtitle, sub_y + 30, sub_font, TEXT_MAIN)

    return img


# 场景渲染器映射
RENDERERS = {
    "promo": render_promo_frame,
    "pain_points": render_pain_points_frame,
    "solution": render_solution_frame,
    "alert_demo": render_alert_demo_frame,
    "kline_demo": render_kline_demo_frame,
    "sentiment_viz": render_sentiment_viz_frame,
    "stock_pool_demo": render_stock_pool_demo_frame,
    "excel_showcase": render_excel_showcase_frame,
    "usage": render_usage_frame,
    "fallback_chain": render_fallback_chain_frame,
}


def render_scene_frames(scene: dict, duration: float, audio_path: Path):
    """渲染单个场景的所有帧"""
    scene_dir = FRAMES_DIR / f"scene_{scene['id']:02d}"
    scene_dir.mkdir(exist_ok=True)

    total_frames = int(duration * FPS)
    renderer = RENDERERS.get(scene["type"], render_excel_showcase_frame)
    narration = scene.get("narration", "")

    for i in range(total_frames):
        progress = i / total_frames
        img = renderer(scene, progress)
        # 字幕（中间 80% 时段显示）
        if 0.1 < progress < 0.9:
            img = render_subtitle_overlay(img, narration, progress)
        img.save(scene_dir / f"frame_{i:05d}.png")

    print(f"  场景 {scene['id']:02d} [{scene['type']}] 已渲染 {total_frames} 帧 ({duration:.1f}s)")


# ============================================================
# 配音生成
# ============================================================
async def generate_audio(scene: dict) -> float:
    """用 edge-tts 生成单个分镜的配音"""
    audio_path = AUDIO_DIR / f"scene_{scene['id']:02d}.mp3"
    text = scene["narration"]
    communicate = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural", rate="-5%")
    await communicate.save(str(audio_path))


def get_audio_duration(audio_path: Path) -> float:
    """获取音频文件时长（秒）"""
    try:
        result = subprocess.run(
            [FFMPEG, "-i", str(audio_path), "-f", "null", "-"],
            capture_output=True, text=True, timeout=10
        )
        import re
        m = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mi * 60 + s
    except Exception:
        pass
    return 5.0


# ============================================================
# 合成视频
# ============================================================
def compose_video(scenes: list, audio_durations: dict):
    """合成最终视频"""
    print("\n=== 开始合成视频 ===")

    scene_videos = []
    for scene in scenes:
        scene_id = scene["id"]
        scene_dir = FRAMES_DIR / f"scene_{scene_id:02d}"
        video_path = AUDIO_DIR / f"scene_{scene_id:02d}.mp4"

        cmd = [
            FFMPEG, "-y",
            "-framerate", str(FPS),
            "-i", str(scene_dir / "frame_%05d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "20",
            "-preset", "medium",
            str(video_path)
        ]
        print(f"  编码场景 {scene_id:02d} -> {video_path.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [错误] 场景 {scene_id:02d} 编码失败: {result.stderr[-500:]}")
            continue
        scene_videos.append((video_path, AUDIO_DIR / f"scene_{scene_id:02d}.mp3"))

    # 拼接
    concat_list = AUDIO_DIR / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for video_path, audio_path in scene_videos:
            merged = video_path.with_suffix(".merged.mp4")
            cmd = [
                FFMPEG, "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(merged)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  [警告] 场景合并音频失败，使用无声视频: {result.stderr[-300:]}")
                merged = video_path
            f.write(f"file '{merged}'\n")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(OUTPUT_MP4)
    ]
    print(f"  最终拼接 -> {OUTPUT_MP4.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [错误] 最终拼接失败: {result.stderr[-500:]}")
        return False

    print(f"\n✅ 视频已生成: {OUTPUT_MP4}")
    print(f"   大小: {OUTPUT_MP4.stat().st_size / 1024 / 1024:.1f} MB")
    return True


# ============================================================
# 主流程
# ============================================================
async def main():
    print("=" * 70)
    print("看盘神器 V2 功能讲解视频生成器 (v4 精美优化版)")
    print("=" * 70)

    # 步骤1: 生成配音
    print("\n=== 步骤 1/3: 生成中文配音 (edge-tts) ===")
    audio_durations = {}
    for scene in SCENES:
        audio_path = AUDIO_DIR / f"scene_{scene['id']:02d}.mp3"
        # 强制重新生成配音（场景内容变化）
        print(f"  生成场景 {scene['id']:02d} 配音...")
        await generate_audio(scene)
        dur = get_audio_duration(audio_path)
        actual_dur = dur + 1.0  # 前后留 0.5s
        audio_durations[scene["id"]] = actual_dur
        print(f"  场景 {scene['id']:02d}: 配音 {dur:.1f}s -> 视频时长 {actual_dur:.1f}s")

    # 步骤2: 渲染帧
    print("\n=== 步骤 2/3: 渲染帧序列 (Pillow) ===")
    for scene in SCENES:
        duration = audio_durations[scene["id"]]
        render_scene_frames(scene, duration, audio_path)

    # 步骤3: 合成视频
    print("\n=== 步骤 3/3: 合成最终视频 (ffmpeg) ===")
    success = compose_video(SCENES, audio_durations)

    if success:
        total_dur = sum(audio_durations.values())
        print("\n" + "=" * 70)
        print(f"🎉 讲解视频生成完成！")
        print(f"   📁 路径: {OUTPUT_MP4}")
        print(f"   ⏱ 总时长: {total_dur:.1f}s ({int(total_dur//60)}分{int(total_dur%60)}秒)")
        print("=" * 70)
    else:
        print("\n❌ 视频生成失败，请检查日志")


if __name__ == "__main__":
    asyncio.run(main())
