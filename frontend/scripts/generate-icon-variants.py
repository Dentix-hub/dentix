"""Generate PWA icon variants from the source 512 icon.

Outputs (frontend/public/icons/):
  icon-192.png            - any-purpose 192 (downscaled source)
  icon-192-maskable.png   - maskable 192 (content in safe zone on brand bg)
  icon-512-maskable.png   - maskable 512 (content in safe zone on brand bg)
  apple-touch-icon-180.png- iOS home screen icon (full-bleed, no transparency)

Maskable safe zone: content must survive a centered circle of 80% diameter.
The DENTIX wordmark is wide, so it is scaled to 62% of the canvas.
"""
from PIL import Image

SRC = "public/icons/icon-512.png"
OUT = "public/icons"
MASKABLE_SCALE = 0.62

src = Image.open(SRC).convert("RGB")
bg = src.getpixel((4, 4))
print(f"background sampled: #{bg[0]:02X}{bg[1]:02X}{bg[2]:02X}")


def maskable(size: int) -> Image.Image:
    canvas = Image.new("RGB", (size, size), bg)
    inner = int(size * MASKABLE_SCALE)
    content = src.resize((inner, inner), Image.LANCZOS)
    offset = (size - inner) // 2
    canvas.paste(content, (offset, offset))
    return canvas


src.resize((192, 192), Image.LANCZOS).save(f"{OUT}/icon-192.png", optimize=True)
maskable(512).save(f"{OUT}/icon-512-maskable.png", optimize=True)
maskable(192).save(f"{OUT}/icon-192-maskable.png", optimize=True)
src.resize((180, 180), Image.LANCZOS).save(f"{OUT}/apple-touch-icon-180.png", optimize=True)
print("generated icon variants")
