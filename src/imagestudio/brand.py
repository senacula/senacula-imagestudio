"""The Senacula Image Studio mark (ADR-070): the senate's table seen from above, a thin ring
with six hollow seats and the presiding dais at the bottom, and on the floor what the product
is; Image Studio puts a picture there. The drawing simplifies as it shrinks instead of being
scaled, so there are four levels, each its own SVG in ``static/brand`` (copied from the family
repository's ``brand/`` folder): large (96 px and up), medium (40-95), small (21-39) and tiny
(20 and under). Every raster in the repository (app icon, home-screen PNGs, Store artwork,
MSIX tiles) is rendered here with Pillow from those SVGs, at the level that fits its size."""

# Copyright 2026 Ratul Roy (royal-programmer) and the Senacula contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import re
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

FAMILY = "Senacula"
PRODUCT = "Image Studio"
FULL_NAME = f"{FAMILY} {PRODUCT}"
VIOLET = "#5B4FD1"  # Senacula
TEAL = "#149A78"  # Image Studio
LIGHT = "#F4F4F5"
INK = "#15161A"
GROUND = "#09090b"

BRAND_DIR = Path(__file__).parent / "static" / "brand"
LEVELS = {"large": "image-tile.svg", "medium": "image-tile-48.svg"}
LEVELS |= {"small": "image-tile-24.svg", "tiny": "image-tile-16.svg"}
# in the tile files the tile colour is also the hollow seats' fill and the dais outline
_TILE_COLOUR = "#149A78"
_FG_COLOUR = "#F4F4F5"


def level_for(size: int) -> str:
    """Which drawing a mark of ``size`` px gets (brand/README.md: never scale the large
    drawing below 96 px)."""
    if size >= 96:
        return "large"
    if size >= 40:
        return "medium"
    if size >= 21:
        return "small"
    return "tiny"


@cache
def _source(level: str) -> str:
    return (BRAND_DIR / LEVELS[level]).read_text(encoding="utf-8")


def mark_svg(
    colour: str = TEAL,
    tile: str | None = None,
    label: str = FULL_NAME,
    size: int = 256,
    level: str | None = None,
) -> str:
    """The mark as SVG text at the level for ``size`` (or an explicit ``level``), without
    fixed width/height so it scales with its box. ``tile`` colours the rounded square behind
    a light mark; without it the mark is drawn in ``colour`` on transparent, seats hollow."""
    svg = _source(level or level_for(size)).strip()
    svg = re.sub(r' width="\d+" height="\d+"', "", svg, count=1)
    svg = svg.replace('aria-label="Senacula"', f'aria-label="{label}"', 1)
    if tile:
        return svg.replace(_TILE_COLOUR, tile).replace(_FG_COLOUR, LIGHT)
    svg = re.sub(r'<rect x="0" y="0" width="64" height="64" rx="14" fill="[^"]+"/>', "", svg)
    svg = svg.replace(
        f'fill="{_TILE_COLOUR}" stroke="{_FG_COLOUR}"', f'fill="none" stroke="{_FG_COLOUR}"'
    )
    svg = re.sub(r' stroke="' + _TILE_COLOUR + r'" stroke-width="[\d.]+"', "", svg)
    return svg.replace(_FG_COLOUR, colour)


def _colour(value: str | None, default: str | None):
    if value is None:
        return default
    if value in ("none", "transparent"):
        return None
    return value


def draw_mark(
    size: int,
    colour: str = TEAL,
    tile: str | None = None,
    scale: float = 1.0,
    level: str | None = None,
):
    """The mark as an RGBA Pillow image of ``size`` px, rendered from the SVG for its level at
    4x and downsampled. ``tile`` fills the rounded square behind a light mark (the app icon);
    ``scale`` shrinks the mark inside the canvas (Store artwork leaves room for text)."""
    from PIL import Image, ImageDraw

    svg = mark_svg(colour, tile, size=int(size * scale), level=level)
    root = ET.fromstring(svg)
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 64 * scale
    off = (s - 64 * u) / 2

    def pt(x: float, y: float) -> tuple[float, float]:
        return (off + x * u, off + y * u)

    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        fill = _colour(el.get("fill"), "#000000")
        stroke = _colour(el.get("stroke"), None)
        sw = float(el.get("stroke-width", 1)) if stroke else 0.0
        half = sw / 2
        if tag == "circle":
            cx, cy, r = (float(el.get(k)) for k in ("cx", "cy", "r"))
            x0, y0 = pt(cx - r - half, cy - r - half)
            x1, y1 = pt(cx + r + half, cy + r + half)
            d.ellipse(
                (x0, y0, x1, y1),
                fill=fill,
                outline=stroke,
                width=max(1, round(sw * u)) if stroke else 0,
            )
        elif tag == "rect":
            x, y, w, h = (float(el.get(k)) for k in ("x", "y", "width", "height"))
            rx = float(el.get("rx", 0))
            x0, y0 = pt(x - half, y - half)
            x1, y1 = pt(x + w + half, y + h + half)
            d.rounded_rectangle(
                (x0, y0, x1, y1),
                radius=int((rx + half) * u),
                fill=fill,
                outline=stroke,
                width=max(1, round(sw * u)) if stroke else 0,
            )
        elif tag == "polyline" and stroke:
            nums = [float(v) for v in re.split(r"[ ,]+", el.get("points", "").strip())]
            pts = [pt(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
            w = max(1, round(sw * u))
            d.line(pts, fill=stroke, width=w, joint="curve")
            for x, y in pts:  # round caps and joins
                d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=stroke)
    return img.resize((size, size), Image.LANCZOS)


def mark_png(size: int, colour: str = TEAL, tile: str | None = None) -> bytes:
    out = io.BytesIO()
    draw_mark(size, colour, tile).save(out, "PNG", optimize=True)
    return out.getvalue()


def _font(size: int, bold: bool):
    from PIL import ImageFont

    candidates = (
        ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    )
    for name in candidates:
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")):
            p = folder / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def lockup(width: int, height: int, background: str = TEAL, with_mark: bool = True):
    """Store artwork: the tile colour as background, the light mark, and the lockup
    "Senacula" (medium) + "Image Studio" (regular) beneath it."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (width, height), background)
    d = ImageDraw.Draw(img)
    short = min(width, height)
    mark_size = int(short * (0.42 if height >= width else 0.5))
    if with_mark:
        mark = draw_mark(mark_size, LIGHT, None)
        mark_y = (
            int(height * 0.22)
            if height >= width
            else int((height - mark_size) / 2) - int(height * 0.12)
        )
        img.alpha_composite(mark, (int((width - mark_size) / 2), max(0, mark_y)))
    f1 = _font(int(short * 0.085), True)
    f2 = _font(int(short * 0.085), False)
    text_y = (
        (int(height * 0.22) + mark_size + int(short * 0.06))
        if with_mark
        else int(height / 2 - short * 0.05)
    )
    w1 = d.textlength(FAMILY, font=f1)
    w2 = d.textlength(PRODUCT, font=f2)
    gap = int(short * 0.025)
    x = int((width - (w1 + gap + w2)) / 2)
    d.text((x, text_y), FAMILY, font=f1, fill=LIGHT)
    d.text((x + w1 + gap, text_y), PRODUCT, font=f2, fill=LIGHT)
    return img


TAGLINE = ("Your own image studio.", "Free, local, honest.")


def _glow(img, centre: tuple[int, int], radius: int, colour: str, peak: float = 0.38) -> None:
    """A soft radial glow of ``colour`` behind the mark: the only gradient allowed."""
    from PIL import Image, ImageDraw, ImageFilter

    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = centre
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=int(255 * peak))
    mask = mask.filter(ImageFilter.GaussianBlur(radius * 0.55))
    layer = Image.new("RGBA", (w, h), colour)
    img.paste(layer, (0, 0), mask)


def _fit_font(draw, text: str, size: int, bold: bool, max_width: float):
    """The largest font at or below ``size`` whose rendering of ``text`` fits ``max_width``."""
    while size > 8:
        f = _font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size = int(size * 0.94)
    return _font(size, bold)


def poster(
    width: int,
    height: int,
    colour: str = TEAL,
    family: str = FAMILY,
    product: str = PRODUCT,
    tagline: tuple[str, str] = TAGLINE,
):
    """Store artwork on the dark ground (ADR-066): the mark in colour over a soft glow,
    "Senacula" in medium weight at about 55% of the product size, the product name large and
    regular, then a two-line tagline with the accent colour on the second line. Nothing sits
    within 8% of an edge. Tall (9:16), wide (16:9) and square (1:1) layouts."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (width, height), GROUND)
    d = ImageDraw.Draw(img)
    margin = 0.08
    if height > width:  # 9:16 poster
        mark_size = int(width * 0.42)
        mark_c = (width // 2, int(height / 3))
        text_w = width * (1 - 2 * margin)
        product_px = int(width * 0.105)
        tag_px = int(width * 0.046)
        text_top = mark_c[1] + mark_size // 2 + int(height * 0.06)
        centre_x = width // 2
    elif width > height:  # 16:9 hero
        mark_size = int(height * 0.5)
        mark_c = (int(width * 0.3), height // 2)
        text_w = width * 0.44
        product_px = int(height * 0.115)
        tag_px = int(height * 0.052)
        text_top = None  # vertically centred block on the right
        centre_x = None
    else:  # 1:1 box art
        mark_size = int(width * 0.36)
        mark_c = (width // 2, int(height * 0.36))
        text_w = width * (1 - 2 * margin)
        product_px = int(width * 0.095)
        tag_px = int(width * 0.042)
        text_top = mark_c[1] + mark_size // 2 + int(height * 0.05)
        centre_x = width // 2
    _glow(img, mark_c, int(mark_size * 0.9), colour)
    mark = draw_mark(mark_size, colour)
    img.alpha_composite(mark, (mark_c[0] - mark_size // 2, mark_c[1] - mark_size // 2))

    f_prod = _fit_font(d, product, product_px, False, text_w)
    f_fam = _fit_font(d, family, int(f_prod.size * 0.55), True, text_w)
    f_tag = _fit_font(d, max(tagline, key=len), tag_px, False, text_w)
    gap = int(f_prod.size * 0.18)
    lines = [
        (family, f_fam, LIGHT),
        (product, f_prod, LIGHT),
        (None, None, int(f_prod.size * 0.45)),  # spacer
        (tagline[0], f_tag, LIGHT),
        (tagline[1], f_tag, colour),
    ]
    heights = [(ln[2] if ln[0] is None else ln[1].size) for ln in lines]
    block_h = sum(heights) + gap * (len(lines) - 1)
    if text_top is None:
        text_top = (height - block_h) // 2
        left = int(width * 0.52)
    else:
        left = None
    y = text_top
    for (text, font, fill), hgt in zip(lines, heights, strict=True):
        if text is not None:
            tw = d.textlength(text, font=font)
            x = left if left is not None else int(centre_x - tw / 2)
            d.text((x, y), text, font=font, fill=fill)
        y += hgt + gap
    return img


_INLINE = re.compile(r'(<svg viewBox="0 0 64 64" aria-hidden="true">).*?(</svg>)', re.S)


def _inline_header(path: Path, colour: str, size: int) -> None:
    """Replace the header's inline mark in an HTML file with the level for its CSS size."""
    svg = mark_svg(colour, size=size)
    body = re.sub(r"^<svg[^>]*>", "", svg).removesuffix("</svg>")
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n") > raw.count(b"\n") // 2
    text = raw.decode("utf-8").replace("\r\n", "\n")
    text = _INLINE.sub(lambda m: m.group(1) + body + m.group(2), text, count=1)
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8") if crlf else text.encode("utf-8"))


def write_all(root: Path) -> list[Path]:
    """Regenerate every raster brand asset in the repository from the SVGs, each at the level
    for its size; and the inline header marks and the website favicon."""
    from PIL import Image

    written: list[Path] = []

    def save(img, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "PNG", optimize=True)
        written.append(path)

    # Windows icon: every standard size in one .ico, each drawn at its own level
    ico = root / "packaging" / "ImageStudio.ico"
    frames = [draw_mark(s, tile=TEAL).convert("RGBA") for s in (16, 24, 32, 48, 64, 128, 256)]
    frames[-1].save(
        ico, format="ICO", sizes=[(f.width, f.height) for f in frames], append_images=frames[:-1]
    )
    written.append(ico)
    # MSIX assets: keep each file's current size; square ones get the tile at their level,
    # the unplated taskbar icon the mark alone, wide ones the lockup
    for p in sorted((root / "packaging" / "msix" / "Assets").glob("*.png")):
        with Image.open(p) as im:
            w, h = im.size
        if "unplated" in p.name:
            save(draw_mark(w, TEAL), p)
        elif w == h:
            save(draw_mark(w, tile=TEAL), p)
        else:
            save(lockup(w, h), p)
    # Store listing artwork
    store = root / "packaging" / "store-assets"
    for name, (w, h) in {
        "box-art-1x1-1080.png": (1080, 1080),
        "box-art-1x1-2160.png": (2160, 2160),
        "poster-9x16-720x1080.png": (720, 1080),
        "poster-9x16-1440x2160.png": (1440, 2160),
        "hero-16x9-1920x1080.png": (1920, 1080),
        "hero-16x9-3840x2160.png": (3840, 2160),
    }.items():
        save(poster(w, h), store / name)
    for size in (71, 150, 300):
        save(draw_mark(size, tile=TEAL), store / f"display-1x1-{size}.png")
    # the website: favicon (tiny level on the tile) and the header mark (small level)
    icon = root / "site" / "assets" / "icon.svg"
    icon.write_text(mark_svg(tile=TEAL, size=16), encoding="utf-8")
    written.append(icon)
    for path, size in ((root / "site" / "index.html", 28),):
        _inline_header(path, TEAL, size)
        written.append(path)
    app = root / "src" / "imagestudio" / "static" / "index.html"
    _inline_header(app, "var(--honey)", 24)
    written.append(app)
    return written


if __name__ == "__main__":
    import sys

    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    for p in write_all(repo):
        print(p.relative_to(repo))
