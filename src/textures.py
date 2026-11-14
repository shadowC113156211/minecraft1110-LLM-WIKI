# -*- coding: utf-8 -*-
"""產生原創的 16×16 像素材質（隨機雜訊）與像素劍鼠標。"""
import random
from PIL import Image

PALETTES = {
    "stone": ["#7f7f7f", "#747474", "#8a8a8a", "#6b6b6b", "#959595"],
    "dirt": ["#866043", "#79553a", "#966c4a", "#5f412b", "#8c6446"],
    "grass": ["#5d9b3a", "#4f8a30", "#6aab44", "#47802a", "#73b34b"],
    "deep": ["#4d4d55", "#44444c", "#575760", "#3b3b42", "#5e5e66"],
    "nether": ["#6f1e1e", "#611a1a", "#7d2525", "#521515", "#873030"],
    "end": ["#dcdca0", "#d2d295", "#e6e6b0", "#c6c688", "#ecebb8"],
    "obsidian": ["#1a0f24", "#140b1c", "#24163a", "#0f0816", "#2e1d47"],
    "plank": ["#a8834e", "#9a7744", "#b48d55", "#8c6b3c", "#bb955c"],
    "gold": ["#c99a2e", "#b88a24", "#d9ad3c", "#a87c1c", "#e3bb4a"],
}


def tile(name, out, seed=7):
    rnd = random.Random(seed + hash(name) % 1000)
    pal = PALETTES[name]
    img = Image.new("RGB", (16, 16))
    for y in range(16):
        for x in range(16):
            w = [40, 20, 18, 12, 10]
            if name == "plank":  # 木紋：水平線條
                c = pal[3] if y % 4 == 3 else pal[rnd.choices(range(5), w)[0] if rnd.random() < .5 else 0]
            else:
                c = pal[rnd.choices(range(5), w)[0]]
            img.putpixel((x, y), tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)))
    if name == "grass_side":  # 草地頂部→泥土（目前不用）
        d = PALETTES["dirt"]
        for y in range(5, 16):
            for x in range(16):
                if y > 4 + rnd.randint(0, 3):
                    c = d[rnd.choices(range(5), [40, 20, 18, 12, 10])[0]]
                    img.putpixel((x, y), tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)))
    img.save(out)


# 原創像素劍（藍色水晶劍身＋金色護手＋木柄），劍尖在左上角 (0,0) 作為點擊熱點
SWORD = [
    "kk..............",
    "kwk.............",
    ".kwbk...........",
    "..kwbk..........",
    "...kwbk.........",
    "....kwbk........",
    ".....kwbk.......",
    "......kwbk......",
    ".......kwbk.gg..",
    "........kwbkgk..",
    ".........kbggk..",
    "..........gghk..",
    "........gggkhhk.",
    "........gkk.khhk",
    "..............kk",
    "................",
]


def cursor(out, blade=("#bff6ff", "#3fd3e0"), scale=2):
    pal = {"k": (20, 20, 30, 255), "w": None, "b": None, "g": (245, 200, 60, 255), "h": (120, 78, 36, 255)}
    hexes = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    pal["w"], pal["b"] = hexes(blade[0]), hexes(blade[1])
    img = Image.new("RGBA", (16 * scale, 16 * scale), (0, 0, 0, 0))
    for y, row in enumerate(SWORD):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((x * scale + dx, y * scale + dy), pal[ch])
    img.save(out)


if __name__ == "__main__":
    import sys, os
    d = sys.argv[1]
    for n in PALETTES:
        tile(n, os.path.join(d, f"tex_{n}.png"))
    cursor(os.path.join(d, "cursor_sword.png"))
    cursor(os.path.join(d, "cursor_sword_hover.png"), blade=("#fff4b0", "#f5b82e"))
    print("ok")
