#!/usr/bin/env python3
import os
from pathlib import Path
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow', '-q'])
    from PIL import Image, ImageDraw, ImageFont

CANDIDATES = [
    ("迪迦奥特曼", 1),
    ("梦比优斯奥特曼", 2),
    ("雷欧奥特曼", 3),
    ("捷德奥特曼", 4),
    ("布莱泽奥特曼", 5),
    ("戴拿奥特曼", 6),
    ("奈克赛斯奥特曼", 7),
    ("盖亚奥特曼", 8),
    ("银河奥特曼", 9),
    ("欧布奥特曼", 10),
    ("赛罗奥特曼", 11),
    ("泽塔奥特曼", 12),
    ("艾克斯奥特曼", 13),
    ("泰迦奥特曼", 14),
    ("希卡利奥特曼", 15),
    ("提欧奥特曼", 16),
    ("高斯奥特曼", 17),
    ("特利迦奥特曼", 18),
    ("阿古茹奥特曼", 19),
    ("麦克斯奥特曼", 20),
]

# Unique color scheme per candidate - distinct colors
COLORS = [
    (99, 102, 241),   # 迪迦 - Indigo
    (59, 130, 246),   # 梦比优斯 - Blue
    (147, 51, 234),   # 雷欧 - Purple
    (236, 72, 153),   # 捷德 - Pink
    (244, 63, 94),    # 布莱泽 - Rose
    (14, 165, 233),   # 戴拿 - Sky
    (6, 182, 212),    # 奈克赛斯 - Cyan
    (16, 185, 129),   # 盖亚 - Emerald
    (132, 204, 22),   # 银河 - Lime
    (250, 204, 21),   # 欧布 - Yellow
    (245, 158, 11),   # 赛罗 - Amber
    (239, 68, 68),    # 泽塔 - Red
    (220, 38, 38),    # 艾克斯 - Dark Red
    (249, 115, 22),   # 泰迦 - Orange
    (234, 179, 8),    # 希卡利 - Gold
    (168, 85, 247),   # 提欧 - Violet
    (139, 92, 246),   # 高斯 - Purple
    (59, 130, 246),   # 特利迦 - Blue
    (236, 72, 153),   # 阿古茹 - Pink
    (6, 182, 212),    # 麦克斯 - Cyan
]

SIZE = 120

def get_char(name):
    """Extract the distinctive first character from the Chinese name."""
    if name.startswith("迪迦"):
        return "迪"
    elif name.startswith("梦比优斯"):
        return "梦"
    elif name.startswith("雷欧"):
        return "雷"
    elif name.startswith("捷德"):
        return "捷"
    elif name.startswith("布莱泽"):
        return "布"
    elif name.startswith("戴拿"):
        return "戴"
    elif name.startswith("奈克赛斯"):
        return "奈"
    elif name.startswith("盖亚"):
        return "盖"
    elif name.startswith("银河"):
        return "银"
    elif name.startswith("欧布"):
        return "欧"
    elif name.startswith("赛罗"):
        return "赛"
    elif name.startswith("泽塔"):
        return "泽"
    elif name.startswith("艾克斯"):
        return "艾"
    elif name.startswith("泰迦"):
        return "泰"
    elif name.startswith("希卡利"):
        return "希"
    elif name.startswith("提欧"):
        return "提"
    elif name.startswith("高斯"):
        return "高"
    elif name.startswith("特利迦"):
        return "特"
    elif name.startswith("阿古茹"):
        return "阿"
    elif name.startswith("麦克斯"):
        return "麦"
    return name[0]

def create_avatar(name, index, color):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = SIZE // 2, SIZE // 2
    radius = SIZE // 2 - 4
    
    # Draw outer glow
    for i in range(3):
        alpha = 80 - i * 25
        glow_radius = radius + 2 + i * 2
        draw.ellipse(
            [cx - glow_radius, cy - glow_radius, cx + glow_radius, cy + glow_radius],
            outline=(*color, alpha),
            width=2
        )
    
    # Draw main circle with gradient effect
    for r in range(radius, radius - 15, -1):
        ratio = (radius - r) / 15
        r_c = int(color[0] * (1 - ratio * 0.3))
        g_c = int(color[1] * (1 - ratio * 0.3))
        b_c = int(color[2] * (1 - ratio * 0.3))
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(r_c, g_c, b_c, 255),
            width=1
        )
    
    # Fill circle
    draw.ellipse(
        [cx - radius + 2, cy - radius + 2, cx + radius - 2, cy + radius - 2],
        fill=(*color, 255)
    )
    
    # Draw inner circle
    inner_radius = radius - 12
    draw.ellipse(
        [cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius],
        outline=(255, 255, 255, 180),
        width=2
    )
    
    # Draw Chinese character
    char = get_char(name)
    try:
        # Try to use system fonts
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 56)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
    except:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 56)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 20)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), char, font=font_large)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Draw character with shadow
    shadow_offset = 2
    draw.text(
        (cx - text_w // 2 + shadow_offset, cy - text_h // 2 - 8 + shadow_offset),
        char,
        font=font_large,
        fill=(0, 0, 0, 100)
    )
    
    # Draw main character
    draw.text(
        (cx - text_w // 2, cy - text_h // 2 - 8),
        char,
        font=font_large,
        fill=(255, 255, 255, 255)
    )
    
    # Draw rank number at bottom
    rank_text = f"#{index}"
    bbox2 = draw.textbbox((0, 0), rank_text, font=font_small)
    rank_w = bbox2[2] - bbox2[0]
    draw.text(
        (cx - rank_w // 2, cy + inner_radius - 25),
        rank_text,
        font=font_small,
        fill=(255, 255, 255, 255)
    )
    
    return img

def main():
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    
    print(f"🎨 Generating {len(CANDIDATES)} Ultraman avatars...")
    
    for idx, (name, number) in enumerate(CANDIDATES):
        color = COLORS[idx]
        img = create_avatar(name, number, color)
        output_path = output_dir / f"ultraman_{number:02d}.png"
        img.save(output_path, 'PNG')
        print(f"  ✓ {name} -> ultraman_{number:02d}.png")
    
    print(f"\n✅ Generated {len(CANDIDATES)} avatars in {output_dir}")

if __name__ == '__main__':
    main()
