"""Original, procedural eye artwork. Output is always a 240×240 RGB image."""
import math
from PIL import Image, ImageDraw


def render_eye(openness, now, side=0, talking=False):
    scale = 2
    canvas = Image.new("RGB", (480, 480), "black")
    draw = ImageDraw.Draw(canvas)

    def box(coords):
        return tuple(int(v * scale) for v in coords)

    if openness < 0.035:
        bob = math.sin(now * 1.6) * 3
        points = [(x * 2, int((126 + bob + 17 * math.sin((x - 32) / 176 * math.pi)) * 2))
                  for x in range(32, 209)]
        draw.line(points, fill=(204, 115, 44), width=8, joint="curve")
        # Soft outer creases, rather than angry eyebrows.
        for x in (41, 193):
            draw.line(box((x, 132 + bob, x - 5, 124 + bob)), fill=(204, 115, 44), width=5)
    else:
        # A 232px circle leaves a small margin for antialiasing on each edge.
        half_height = 116 * max(0.02, min(1, openness))
        bounds = (4, 120 - half_height, 236, 120 + half_height)
        layer = Image.new("RGB", canvas.size, (246, 234, 211))
        eye = ImageDraw.Draw(layer)
        gx = 120 + math.sin(now * 0.46) * 15 + (2 if side else -2)
        gy = 120 + math.sin(now * 0.31) * 6
        eye.ellipse(box((gx - 73, gy - 73, gx + 73, gy + 73)), fill=(130, 56, 17))
        eye.ellipse(box((gx - 65, gy - 65, gx + 65, gy + 65)), fill=(244, 133, 31))
        # Radial detail stays legible on a small physical screen.
        for i in range(36):
            angle = i * math.tau / 36
            line = (gx + math.cos(angle) * 44, gy + math.sin(angle) * 44,
                    gx + math.cos(angle) * 62, gy + math.sin(angle) * 62)
            eye.line(box(line), fill=(189, 77, 15), width=2)
        pupil = 34 + (2 * math.sin(now * 10) if talking else math.sin(now) * 1.5)
        eye.ellipse(box((gx - pupil, gy - pupil, gx + pupil, gy + pupil)), fill=(4, 13, 12))
        eye.ellipse(box((gx - 30, gy - 39, gx - 7, gy - 16)), fill=(255, 253, 237))
        eye.ellipse(box((gx + 16, gy + 14, gx + 25, gy + 23)), fill=(255, 218, 158))
        mask = Image.new("L", canvas.size)
        ImageDraw.Draw(mask).ellipse(box(bounds), fill=255)
        canvas.paste(layer, (0, 0), mask)
        draw = ImageDraw.Draw(canvas)
        draw.ellipse(box(bounds), outline=(204, 115, 44), width=4)
    return canvas.resize((240, 240), Image.Resampling.LANCZOS)
