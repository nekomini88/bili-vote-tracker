from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math

out = Path('/root/bili-vote-tracker/frontend/assets/heroes')

# Each candidate gets a distinct Hue for HSL-based Ultraman-style avatar
hues = [
    180,  # Tiga - cyan
    60,   # Mebius - gold
    0,    # Leo - red
    30,   # Geed - blue-green
    120,  # Blazar - purple-blue
    40,   # Dyna - orange
    200,  # Nexus - indigo
    90,   # Gaia - green
    220,  # Ginga - violet
    35,   # Orb - amber
    270,  # Zero - purple
    15,   # Zeta - crimson
    160,  # X - teal
    330,  # Taiga - rose
    190,  # Hikari - sky
    50,   # Dea - lime
    110,  # Cosmos - emerald
    25,   # Trigger - coral
    300,  # Agul - magenta
    85,   # Max - chartreuse
]

def hsl_to_rgb(h, s, l):
    c = (1 - abs(2*l - 1)) * s
    x = c * (1 - abs((h/60) % 2 - 1))
    m = l - c/2
    if h < 60: r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else: r,g,b = c,0,x
    return int((r+m)*255), int((g+m)*255), int((b+m)*255)

def make_avatar(hue, index):
    size = 200
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    main_rgb = hsl_to_rgb(hue % 360, 0.7, 0.55)
    light_rgb = hsl_to_rgb(hue % 360, 0.5, 0.75)
    dark_rgb = hsl_to_rgb(hue % 360, 0.8, 0.35)
    
    # Main face circle with thicker border
    d.ellipse([6, 6, size-7, size-7], fill=light_rgb + (255,), outline=dark_rgb + (255,), width=6)
    
    # Ultraman-style face slots (eyes)
    eye_y = 80
    left_eye = (65, eye_y, 95, eye_y+35)
    right_eye = (105, eye_y, 135, eye_y+35)
    
    for ex1, ey1, ex2, ey2 in [left_eye, right_eye]:
        d.ellipse([ex1, ey1, ex2, ey2], fill=dark_rgb + (255,))
        d.ellipse([ex1+6, ey1+8, ex1+20, ey1+22], fill=(255, 255, 255, 220))
    
    # Nose/visor line
    d.polygon([
        (size//2, 115),
        (size//2-8, 145),
        (size//2+8, 145)
    ], fill=dark_rgb + (255,))
    
    # Mouth
    d.arc([75, 135, 125, 165], start=10, end=170, fill=dark_rgb + (255,), width=4)
    
    # Ultraman crest on forehead (distinctive triangle)
    d.polygon([
        (size//2, 25),
        (size//2-12, 58),
        (size//2+12, 58)
    ], fill=(255, 255, 255, 245), outline=(220, 220, 220, 255), width=2)
    
    # Color dot on crest
    d.ellipse([size//2-6, 38, size//2+6, 50], fill=main_rgb + (255,))
    
    # Number on forehead for uniqueness
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        bb = d.textbbox((0,0), str(index), font=font)
        tw = bb[2]-bb[0]
        d.text((size//2 - tw/2, 52), str(index), fill=(40,40,40,255), font=font)
    except Exception:
        pass
    
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / f'ultraman_{str(index).zfill(2)}.png')

for i, hue in enumerate(hues, start=1):
    make_avatar(hue, i)

print('generated', len(list(out.glob('ultraman_*.png'))), 'avatars')
print('sample md5:', __import__('hashlib').md5((out / 'ultraman_01.png').read_bytes()).hexdigest())
