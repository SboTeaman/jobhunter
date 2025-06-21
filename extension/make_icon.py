"""Generuje ikonę 48x48 PNG dla rozszerzenia Chrome.
Uruchom raz: python make_icon.py"""
import struct, zlib, base64

def _png_chunk(name, data):
    c = zlib.crc32(name + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

def make_png_48():
    w = h = 48
    # Proste "J" na granatowym tle
    import os
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (w, h), (15, 18, 22, 255))
        d = ImageDraw.Draw(img)
        d.ellipse([2,2,45,45], fill=(79, 140, 255, 255))
        d.text((13, 10), "JH", fill=(255,255,255,255))
        img.save("icon48.png")
        print("icon48.png wygenerowany (PIL)")
        return
    except ImportError:
        pass
    # Fallback: czyste PNG 48x48 z gradientem
    raw = b""
    for y in range(h):
        raw += b"\x00"
        for x in range(w):
            r = int(79 + (x/w)*60)
            g = int(140 - (y/h)*30)
            b2 = 255
            raw += bytes([r, g, b2, 255])
    compressed = zlib.compress(raw)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", compressed)
            + _png_chunk(b"IEND", b""))
    with open("icon48.png", "wb") as f:
        f.write(data)
    print("icon48.png wygenerowany (fallback)")

make_png_48()
