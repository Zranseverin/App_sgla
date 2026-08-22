"""Build the CleanGo customer-journey promotional video from generated scenes."""

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "apps" / "entreprises" / "static" / "entreprises" / "media"
SCENES_DIR = MEDIA / "video"
OUTPUT = MEDIA / "cleango-parcours-client.mp4"
LOGO_PATH = ROOT / "static" / "branding" / "cleango-logo.png"

WIDTH, HEIGHT = 1280, 720
FPS = 24
SCENE_SECONDS = 3.8
FADE_SECONDS = 0.45
GREEN = (10, 122, 72)
LIME = (50, 205, 126)

SCENES = [
    ("scene-01-voiture-sale.png", "Une voiture sale...", "et aucune idée de l’endroit où aller."),
    ("scene-02-decouverte-cleango.png", "Une recherche suffit", "Il découvre CleanGo sur son téléphone."),
    ("scene-03-localisation-catalogue.png", "Le bon lavage, tout près", "Carte, catalogues et prix sont visibles immédiatement."),
    ("scene-04-itineraire.png", "L’itinéraire est prêt", "CleanGo le guide jusqu’à la station choisie."),
    ("scene-05-enregistrement.png", "Un accueil rapide", "La caissière enregistre le client et son véhicule."),
    ("scene-06-lavage.png", "Place au lavage", "Le véhicule est pris en charge par des professionnels."),
    ("scene-07-paiement-wave.png", "Paiement Wave confirmé", "Il repart satisfait, avec une voiture impeccable."),
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


FONT_BRAND = font("segoeuib.ttf", 38)
FONT_TITLE = font("segoeuib.ttf", 50)
FONT_SUBTITLE = font("segoeui.ttf", 26)
FONT_STEP = font("segoeuib.ttf", 18)


def cover(image: Image.Image, scale: float, pan: float) -> Image.Image:
    image = image.convert("RGB")
    base_scale = max(WIDTH / image.width, HEIGHT / image.height)
    resize_scale = base_scale * scale
    resized = image.resize(
        (round(image.width * resize_scale), round(image.height * resize_scale)),
        Image.Resampling.LANCZOS,
    )
    max_x = max(0, resized.width - WIDTH)
    max_y = max(0, resized.height - HEIGHT)
    x = round(max_x * (0.30 + 0.40 * pan))
    y = round(max_y * 0.48)
    return resized.crop((x, y, x + WIDTH, y + HEIGHT))


def rounded_panel(frame: Image.Image, opacity: int) -> None:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((54, 500, 980, 664), radius=25, fill=(3, 20, 14, opacity))
    frame.paste(overlay, (0, 0), overlay)


def add_text(frame: Image.Image, index: int, title: str, subtitle: str, alpha: float) -> None:
    rounded_panel(frame, round(208 * alpha))
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    white = (255, 255, 255, round(255 * alpha))
    soft = (226, 239, 232, round(255 * alpha))
    green = (*LIME, round(255 * alpha))

    draw.rounded_rectangle((54, 38, 270, 92), radius=27, fill=(3, 20, 14, round(205 * alpha)))
    draw.ellipse((70, 52, 96, 78), fill=green)
    draw.text((108, 45), "CleanGo", font=FONT_BRAND, fill=white)

    draw.text((84, 522), f"0{index + 1}", font=FONT_STEP, fill=green)
    draw.text((84, 552), title, font=FONT_TITLE, fill=white)
    draw.text((86, 616), subtitle, font=FONT_SUBTITLE, fill=soft)

    total = len(SCENES)
    gap, dot_w = 9, 44
    start_x = WIDTH - 60 - (total * dot_w + (total - 1) * gap)
    for step in range(total):
        color = green if step <= index else (255, 255, 255, round(90 * alpha))
        draw.rounded_rectangle(
            (start_x + step * (dot_w + gap), 654, start_x + step * (dot_w + gap) + dot_w, 660),
            radius=3,
            fill=color,
        )
    frame.paste(overlay, (0, 0), overlay)


def scene_frame(image: Image.Image, index: int, title: str, subtitle: str, local_t: float) -> Image.Image:
    progress = local_t / SCENE_SECONDS
    eased = 0.5 - 0.5 * math.cos(math.pi * progress)
    frame = cover(image, 1.035 + 0.055 * eased, eased if index % 2 == 0 else 1 - eased)
    frame = ImageEnhance.Color(frame).enhance(1.04)

    fade = min(1.0, local_t / FADE_SECONDS, (SCENE_SECONDS - local_t) / FADE_SECONDS)
    add_text(frame, index, title, subtitle, max(0.0, fade))
    if fade < 1:
        black = Image.new("RGB", frame.size, (3, 20, 14))
        frame = Image.blend(black, frame, max(0.0, fade))
    return frame


def closing_frame(local_t: float, seconds: float = 4.5) -> Image.Image:
    frame = Image.new("RGB", (WIDTH, HEIGHT), (3, 20, 14))
    draw = ImageDraw.Draw(frame)
    glow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((820, -240, 1480, 420), fill=(10, 122, 72, 90))
    gd.ellipse((-250, 450, 450, 1050), fill=(50, 205, 126, 45))
    frame.paste(glow, (0, 0), glow)
    cx = WIDTH // 2
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo.thumbnail((132, 132), Image.Resampling.LANCZOS)
    frame.paste(logo, (cx - logo.width // 2, 58), logo)
    logo.close()
    draw.text((cx, 202), "CleanGo", font=font("segoeuib.ttf", 66), fill="white", anchor="ma")
    draw.text((cx, 278), "L’idée du lavage en un clic", font=font("segoeuib.ttf", 36), fill=LIME, anchor="ma")
    draw.rounded_rectangle((268, 351, 1012, 579), radius=28, fill=(9, 43, 31))
    draw.text((cx, 397), "www.cleango.ci", font=font("segoeuib.ttf", 29), fill="white", anchor="mm")
    draw.text((cx, 466), "+225 01 40 00 45 09", font=font("segoeui.ttf", 27), fill=(226, 239, 232), anchor="mm")
    draw.text((cx, 530), "info@cleango.ci", font=font("segoeui.ttf", 27), fill=(226, 239, 232), anchor="mm")
    draw.text((cx, 646), "Trouvez. Suivez. Lavez.", font=font("segoeuib.ttf", 25), fill="white", anchor="mm")
    return frame


def main() -> None:
    images = [Image.open(SCENES_DIR / filename) for filename, _, _ in SCENES]
    writer = imageio_ffmpeg.write_frames(
        str(OUTPUT),
        (WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        output_params=["-crf", "21", "-preset", "medium", "-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        frames_per_scene = round(SCENE_SECONDS * FPS)
        for index, ((_, title, subtitle), image) in enumerate(zip(SCENES, images)):
            for frame_number in range(frames_per_scene):
                frame = scene_frame(image, index, title, subtitle, frame_number / FPS)
                writer.send(frame.tobytes())
        closing_seconds = 4.5
        for frame_number in range(round(closing_seconds * FPS)):
            writer.send(closing_frame(frame_number / FPS, closing_seconds).tobytes())
    finally:
        writer.close()
        for image in images:
            image.close()
    print(f"Video created: {OUTPUT}")


if __name__ == "__main__":
    main()
