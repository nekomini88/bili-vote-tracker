from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

out = Path('frontend/assets/heroes')
colors = [
    '#7ec8e3','#b39ddb','#80cbc4','#ffab91','#fff59d','#90caf9','#ce93d8','#a5d6a7',
    '#ffcc80','#80deea','#f48fb1','#b0bec5','#9fa8da','#81c784','#64b5f6','#e6ee9c',
    '#ff8a65','#4dd0e1','#ba68c8','#4db6ac'
]

def make_face(color: str, index: int):
    size = 200
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Color fill with soft rounded edges
    base = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(base)
    bd.ellipse([12, 12, size - 12, size - 12], fill=color, outline=(255,255,255,55), width=2)
    base = base.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.alpha_composite(img, base)
    d = ImageDraw.Draw(img)

    # Head oval
    d.ellipse([52, 38, 148, 138], fill=(255, 245, 235, 255), outline=(238, 224, 210, 255), width=2)
    d.chord([58, 42, 142, 134], start=210, end=-30, fill=(255, 245, 235, 255), outline=(238, 224, 210, 255))

    # Eyes
    d.ellipse([78, 90, 98, 110], fill=(30, 30, 30, 255))
    d.ellipse([102, 90, 122, 110], fill=(30, 30, 30, 255))
    d.ellipse([82, 94, 90, 102], fill=(255, 255, 255, 255))
    d.ellipse([106, 94, 114, 102], fill=(255, 255, 255, 255))

    # Nose
    d.polygon([(96, 118), (104, 118), (100, 128)], fill=(220, 200, 180, 255))

    # Mouth
    d.arc([88, 126, 112, 146], start=10, end=170, fill=(180, 110, 110, 255), width=3)

    # Blush
    for cx, cy in [(72, 124), (128, 124)]:
        d.ellipse([cx - 6, cy - 4, cx + 6, cy + 4], fill=(255, 160, 160, 110))

    # Letter code on top: Ultraman letter, ensure uniqueness
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        letter = chr(65 + (index - 1) % 26)
        bb = d.textbbox((0, 0), letter, font=font)
        tw = bb[2] - bb[0]
        d.text((size / 2 - tw / 2, 16), letter, fill=(255, 255, 255, 235), font=font)
    except Exception:
        pass

    out.mkdir(parents=True, exist_ok=True)
    img.save(out / f'ultraman_{str(index).zfill(2)}.png')

for i, color in enumerate(colors, start=1):
    make_face(color, i)

print('generated', len(list(out.glob('ultraman_*.png'))))
