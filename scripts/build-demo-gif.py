#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "layman-demo.gif"
SCENES = [
    ("From idea to verified software", ["You describe the outcome in ordinary language", "Layman chooses the smallest reliable path"]),
    ("Understand where the project stands", ["$layman-status checks bounded repository evidence", "Stage: building  |  Next: verify one user scenario"]),
    ("Load only what the task needs", ["context + feature workflow + verification", "No whole-repository scan or repeated logs"]),
    ("Automatic Plus execution", ["$layman-auto keeps the original task unchanged", "balanced route  |  ephemeral  |  API billing removed"]),
    ("Transparent API mode", ["model=auto with opt-in safe context cleanup", "High-risk work always keeps the deep safety floor"]),
    ("Verified, private, and reversible", ["Outcome + checks + one next step", "No prompt/code telemetry; uninstall restores settings"]),
]


def font(size: int):
    candidates = [Path("C:/Windows/Fonts/consola.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    title_font, body_font, small_font = font(30), font(22), font(15)
    frames = []
    for index, (title, lines) in enumerate(SCENES, 1):
        frame = Image.new("RGB", (1000, 560), "#0b1020")
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((42, 38, 958, 522), radius=20, fill="#111827", outline="#334155", width=2)
        draw.ellipse((72, 68, 88, 84), fill="#fb7185")
        draw.ellipse((98, 68, 114, 84), fill="#fbbf24")
        draw.ellipse((124, 68, 140, 84), fill="#34d399")
        draw.text((72, 120), title, font=title_font, fill="#f8fafc")
        y = 205
        for line in lines:
            draw.text((84, y), f"> {line}", font=body_font, fill="#a7f3d0")
            y += 74
        draw.text((72, 474), f"Layman 1.0  |  step {index}/{len(SCENES)}", font=small_font, fill="#94a3b8")
        draw.text((610, 474), "Illustrated walkthrough - no model calls", font=small_font, fill="#64748b")
        frames.append(frame)
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=5000, loop=0, optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
