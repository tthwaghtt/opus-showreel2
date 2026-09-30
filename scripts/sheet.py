"""Compose review renders into one labelled contact sheet (system python + Pillow).

    python3 scripts/sheet.py <tag> <title> [panel:label ...]
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "renders")
tag, title = sys.argv[1], sys.argv[2]
panels = [a.split(":", 1) for a in sys.argv[3:]] or [["front", "FRONT · ORTHO"], ["side", "LEFT · ORTHO"],
                                                      ["34", "3/4 · 62 mm"], ["sil", "SILHOUETTE"]]


def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F, FS = font(15), font(12)
ims = []
for key, label in panels:
    im = Image.open(os.path.join(R, f"{tag}_{key}.png")).convert("RGBA")
    bgc = (236, 236, 232, 255) if key == "sil" else (62, 66, 72, 255)
    bg = Image.new("RGBA", im.size, bgc)
    if key not in ("sil",):
        # soft vertical gradient behind clay renders
        g = Image.linear_gradient("L").resize(im.size)
        top = Image.new("RGBA", im.size, (84, 89, 96, 255))
        bg = Image.composite(bg, top, g)
    bg.alpha_composite(im)
    ims.append((bg.convert("RGB"), label))
h = max(i.size[1] for i, _ in ims)
pad, head = 14, 46
W = sum(i.size[0] for i, _ in ims) + pad * (len(ims) + 1)
sheet = Image.new("RGB", (W, h + head + pad * 2), (12, 14, 17))
d = ImageDraw.Draw(sheet)
d.text((pad, 14), title, font=F, fill=(227, 230, 233))
x = pad
for im, label in ims:
    sheet.paste(im, (x, head))
    d.rectangle([x, head, x + im.size[0] - 1, head + im.size[1] - 1], outline=(38, 44, 53))
    d.text((x + 10, head + 10), label, font=FS, fill=(92, 200, 238) if "SIL" not in label else (20, 20, 20))
    x += im.size[0] + pad
out = os.path.join(R, f"{tag}_sheet.png")
sheet.save(out)
print(out, sheet.size)
