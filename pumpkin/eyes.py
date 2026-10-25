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
        draw.line(points, fill=(111, 165, 96), width=8, joint="curve")
        # Soft outer creases, rather than angry eyebrows.
        for x in (41, 193):
            draw.line(box((x, 132 + bob, x - 5, 124 + bob)), fill=(111, 165, 96), width=5)
    else:
        half_height = 70 * max(0.02, min(1, openness))
        bounds = (24, 122 - half_height, 216, 122 + half_height)
        layer = Image.new("RGB", canvas.size, (223, 232, 198))
        eye = ImageDraw.Draw(layer)
        gx = 120 + math.sin(now * 0.46) * 15 + (2 if side else -2)
        gy = 123 + math.sin(now * 0.31) * 6
        eye.ellipse(box((gx - 55, gy - 55, gx + 55, gy + 55)), fill=(26, 89, 49))
        eye.ellipse(box((gx - 48, gy - 48, gx + 48, gy + 48)), fill=(108, 197, 81))
        # Radial detail stays legible on a small physical screen.
        for i in range(36):
            angle = i * math.tau / 36
            line = (gx + math.cos(angle) * 34, gy + math.sin(angle) * 34,
                    gx + math.cos(angle) * 46, gy + math.sin(angle) * 46)
            eye.line(box(line), fill=(56, 137, 65), width=2)
        pupil = 25 + (2 * math.sin(now * 10) if talking else math.sin(now) * 1.5)
        eye.ellipse(box((gx - pupil, gy - pupil, gx + pupil, gy + pupil)), fill=(4, 13, 12))
        eye.ellipse(box((gx - 22, gy - 29, gx - 5, gy - 12)), fill=(250, 255, 230))
        eye.ellipse(box((gx + 12, gy + 10, gx + 19, gy + 17)), fill=(204, 241, 191))
        mask = Image.new("L", canvas.size)
        ImageDraw.Draw(mask).ellipse(box(bounds), fill=255)
        canvas.paste(layer, (0, 0), mask)
        draw = ImageDraw.Draw(canvas)
        draw.ellipse(box(bounds), outline=(94, 139, 75), width=4)
    return canvas.resize((240, 240), Image.Resampling.LANCZOS)
