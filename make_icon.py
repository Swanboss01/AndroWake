"""Génère icon.ico (robot Android stylisé + symbole d'alimentation) : python make_icon.py"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = 512


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=(24, 32, 48, 255))
    green = (61, 220, 132, 255)
    # tête (demi-disque) + antennes
    d.pieslice((116, 150, 396, 430), 180, 360, fill=green)
    d.line((176, 160, 148, 108), fill=green, width=14)
    d.line((336, 160, 364, 108), fill=green, width=14)
    # yeux
    for cx in (206, 306):
        d.ellipse((cx - 14, 212, cx + 14, 240), fill=(24, 32, 48, 255))
    # symbole power sous la tête
    cx, cy, r = 256, 345, 62
    d.arc((cx - r, cy - r, cx + r, cy + r), -50, 230, fill=green, width=22)
    d.line((cx, cy - r - 8, cx, cy - 4), fill=green, width=22)
    return img


if __name__ == "__main__":
    draw().save(os.path.join(HERE, "icon.ico"),
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon.ico créé")
