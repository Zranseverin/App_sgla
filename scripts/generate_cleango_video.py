from pathlib import Path
import math
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "apps" / "entreprises" / "static" / "entreprises" / "media"
LOGO_PATH = ROOT / "static" / "branding" / "cleango-logo.png"
WASH_PATH = MEDIA / "publicite-lavage.png"
MANAGER_PATH = MEDIA / "publicite-gestion.png"
OUTPUT = MEDIA / "cleango-presentation.mp4"

WIDTH, HEIGHT = 1280, 720
FPS = 15
GREEN = "#087a4b"
GREEN_LIGHT = "#12c777"
ORANGE = "#ff7417"
NAVY = "#12372b"
WHITE = "#ffffff"
MUTED = "#d8eee3"


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def crop_logo():
    image = Image.open(LOGO_PATH).convert("RGBA")
    rgb = image.convert("RGB")
    mask = Image.new("L", image.size, 0)
    pixels, mask_pixels = rgb.load(), mask.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            if min(r, g, b) < 245:
                mask_pixels[x, y] = 255
    bbox = mask.getbbox()
    return image.crop(bbox) if bbox else image


LOGO = crop_logo()
WASH = Image.open(WASH_PATH).convert("RGB")
MANAGER = Image.open(MANAGER_PATH).convert("RGB")


def cover(image, zoom=1.0, offset_x=0.5, offset_y=0.5):
    scale = max(WIDTH / image.width, HEIGHT / image.height) * zoom
    size = (round(image.width * scale), round(image.height * scale))
    resized = image.resize(size, Image.Resampling.LANCZOS)
    left = round((resized.width - WIDTH) * offset_x)
    top = round((resized.height - HEIGHT) * offset_y)
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def multiline(draw, text, xy, max_chars, size, fill=WHITE, bold=False, spacing=8):
    lines = textwrap.wrap(text, max_chars)
    draw.multiline_text(xy, "\n".join(lines), font=font(size, bold), fill=fill, spacing=spacing)


def brand(frame):
    logo = LOGO.copy()
    logo.thumbnail((48, 62), Image.Resampling.LANCZOS)
    plate = Image.new("RGBA", (62, 62), WHITE)
    plate.alpha_composite(logo, ((62 - logo.width) // 2, (62 - logo.height) // 2))
    frame.paste(plate.convert("RGB"), (54, 38))
    draw = ImageDraw.Draw(frame)
    draw.text((128, 42), "CleanGo", font=font(25, True), fill=WHITE)
    draw.text((128, 73), "L’idée du lavage en un clic", font=font(13), fill=MUTED)


def progress(frame, index, total):
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, HEIGHT - 7, WIDTH, HEIGHT), fill="#ffffff35")
    draw.rectangle((0, HEIGHT - 7, round(WIDTH * (index / total)), HEIGHT), fill=ORANGE)


def title_frame(t):
    frame = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(frame)
    for i in range(7):
        x = 830 + i * 36 + math.sin(t * 2 + i) * 12
        draw.arc((x, -120 + i * 18, x + 480, 530 + i * 18), 95, 260, fill=ORANGE if i < 3 else GREEN_LIGHT, width=18)
    logo = LOGO.copy()
    logo.thumbnail((220, 300), Image.Resampling.LANCZOS)
    panel = Image.new("RGBA", (260, 330), WHITE)
    panel.alpha_composite(logo, ((260 - logo.width) // 2, (330 - logo.height) // 2))
    frame.paste(panel.convert("RGB"), (115, 170))
    draw.text((430, 210), "CleanGo", font=font(66, True), fill=WHITE)
    multiline(draw, "L’idée du lavage en un clic", (435, 300), 32, 36, ORANGE, True)
    draw.text((438, 375), "Découvrez l’application qui rapproche les automobilistes", font=font(19), fill=MUTED)
    draw.text((438, 406), "et les professionnels du lavage.", font=font(19), fill=MUTED)
    return frame


def locate_frame(t):
    frame = cover(WASH, 1.05 + t * .025, .56, .5)
    overlay = Image.new("RGBA", frame.size, (7, 43, 31, 170))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
    brand(frame)
    draw = ImageDraw.Draw(frame)
    draw.text((68, 185), "01", font=font(17, True), fill=ORANGE)
    multiline(draw, "Trouvez une station proche", (68, 220), 24, 45, WHITE, True)
    multiline(draw, "Activez votre position, consultez la carte et contactez rapidement une station disponible.", (70, 350), 48, 22, MUTED)
    rounded(draw, (70, 505, 340, 560), 9, ORANGE)
    draw.text((98, 522), "Explorer les stations  →", font=font(17, True), fill=WHITE)
    return frame


def signup_frame(t):
    frame = Image.new("RGB", (WIDTH, HEIGHT), "#f5faf7")
    draw = ImageDraw.Draw(frame)
    draw.ellipse((760, -180, 1400, 460), fill="#e5f8ed")
    draw.ellipse((-230, 470, 390, 1090), fill="#fff0e3")
    draw.text((68, 50), "CleanGo", font=font(25, True), fill=GREEN)
    draw.text((68, 82), "L’idée du lavage en un clic", font=font(13), fill="#628073")
    draw.text((68, 180), "02", font=font(17, True), fill=ORANGE)
    multiline(draw, "Inscrivez votre entreprise", (68, 215), 27, 45, NAVY, True)
    multiline(draw, "Créez votre espace, ajoutez vos types de lavage et leurs tarifs, puis rendez votre station visible.", (70, 348), 48, 21, "#587267")
    x = 770 + round(math.sin(t * 2) * 6)
    rounded(draw, (x, 125, x + 390, 600), 22, WHITE, "#d8e8df", 2)
    draw.text((x + 35, 165), "Créer mon entreprise", font=font(23, True), fill=NAVY)
    fields = ["Nom de l’entreprise", "Téléphone", "Adresse", "Plan CleanGo"]
    for i, label in enumerate(fields):
        top = 230 + i * 74
        draw.text((x + 35, top), label, font=font(12, True), fill="#587267")
        rounded(draw, (x + 35, top + 22, x + 355, top + 58), 6, "#f7faf8", "#dbe7e0")
    rounded(draw, (x + 35, 536, x + 355, 575), 7, GREEN)
    draw.text((x + 119, 548), "Commencer", font=font(14, True), fill=WHITE)
    return frame


def manage_frame(t):
    frame = cover(MANAGER, 1.05 + t * .02, .48, .5)
    overlay = Image.new("RGBA", frame.size, (5, 32, 23, 125))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
    brand(frame)
    draw = ImageDraw.Draw(frame)
    rounded(draw, (710, 145, 1200, 595), 18, "#ffffffed")
    draw.text((750, 185), "03", font=font(17, True), fill=ORANGE)
    multiline(draw, "Gérez chaque passage", (750, 220), 24, 39, NAVY, True)
    items = [
        ("✓", "Client et véhicule"),
        ("✓", "Type de lavage et montant"),
        ("✓", "Mode de règlement"),
        ("✓", "Commission du laveur"),
    ]
    for i, (icon, label) in enumerate(items):
        y = 350 + i * 47
        draw.ellipse((750, y, 776, y + 26), fill="#e2f6ea")
        draw.text((756, y + 3), icon, font=font(13, True), fill=GREEN)
        draw.text((790, y + 3), label, font=font(17, True), fill="#4b665a")
    return frame


def dashboard_frame(t):
    frame = Image.new("RGB", (WIDTH, HEIGHT), "#eff5f1")
    draw = ImageDraw.Draw(frame)
    brand_panel = Image.new("RGB", (WIDTH, 118), NAVY)
    frame.paste(brand_panel, (0, 0))
    brand(frame)
    draw = ImageDraw.Draw(frame)
    draw.text((68, 160), "04", font=font(17, True), fill=ORANGE)
    draw.text((68, 194), "Pilotez vos performances", font=font(42, True), fill=NAVY)
    draw.text((70, 252), "Visualisez vos lavages, vos encaissements et vos commissions.", font=font(19), fill="#5b7468")
    cards = [
        ("Lavages du mois", "148", GREEN),
        ("Chiffre d’affaires", "2 475 000 FCFA", ORANGE),
        ("Taux terminé", "87 %", "#2769c7"),
    ]
    for i, (label, value, color) in enumerate(cards):
        x = 70 + i * 390
        rounded(draw, (x, 315, x + 355, 455), 13, WHITE, "#dbe6df")
        draw.ellipse((x + 24, 340, x + 58, 374), fill=color)
        draw.text((x + 75, 337), label, font=font(14, True), fill="#60766c")
        draw.text((x + 24, 390), value, font=font(25, True), fill=NAVY)
    points = [(95, 605), (250, 565), (405, 585), (560, 510), (715, 535), (870, 465), (1030, 490), (1180, 410)]
    shifted = [(x, y + round(math.sin(t * 2 + x / 140) * 3)) for x, y in points]
    draw.line(shifted, fill=GREEN, width=5, joint="curve")
    for x, y in shifted:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ORANGE)
    return frame


def final_frame(t):
    frame = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(frame)
    logo = LOGO.copy()
    logo.thumbnail((170, 245), Image.Resampling.LANCZOS)
    plate = Image.new("RGBA", (210, 270), WHITE)
    plate.alpha_composite(logo, ((210 - logo.width) // 2, (270 - logo.height) // 2))
    frame.paste(plate.convert("RGB"), (535, 80))
    draw.text((468, 385), "CleanGo", font=font(63, True), fill=WHITE)
    draw.text((386, 470), "L’idée du lavage en un clic", font=font(31, True), fill=ORANGE)
    rounded(draw, (420, 555, 860, 615), 10, GREEN)
    draw.text((493, 574), "cleango.severinzran.ci", font=font(20, True), fill=WHITE)
    return frame


SCENES = [
    (4, title_frame),
    (5, locate_frame),
    (5, signup_frame),
    (5, manage_frame),
    (5, dashboard_frame),
    (4, final_frame),
]


def main():
    MEDIA.mkdir(parents=True, exist_ok=True)
    total_frames = sum(seconds * FPS for seconds, _ in SCENES)
    writer = imageio_ffmpeg.write_frames(
        str(OUTPUT),
        (WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        quality=7,
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)
    frame_index = 0
    for duration, renderer in SCENES:
        scene_frames = duration * FPS
        for local_index in range(scene_frames):
            t = local_index / FPS
            frame = renderer(t)
            fade = min(local_index / 8, (scene_frames - 1 - local_index) / 8, 1)
            if fade < 1:
                frame = ImageEnhance.Brightness(frame).enhance(max(fade, 0))
            frame_index += 1
            progress(frame, frame_index, total_frames)
            writer.send(frame.tobytes())
    writer.close()
    print(f"Vidéo créée : {OUTPUT}")


if __name__ == "__main__":
    main()
