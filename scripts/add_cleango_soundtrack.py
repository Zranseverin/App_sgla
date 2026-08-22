"""Create an original music bed and mix it with the CleanGo female narration."""

from pathlib import Path
import math
import struct
import subprocess
import wave

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "apps" / "entreprises" / "static" / "entreprises" / "media"
VIDEO_DIR = MEDIA / "video"
VIDEO = MEDIA / "cleango-parcours-client.mp4"
VOICE = VIDEO_DIR / "cleango-voix-feminine.mp3"
MUSIC = VIDEO_DIR / "cleango-musique-originale.wav"
MIXED = MEDIA / "cleango-parcours-client-son.mp4"

SAMPLE_RATE = 44_100
DURATION = 31.1


def make_music() -> None:
    """Generate a bright, royalty-free pop bed from simple synthesized instruments."""
    chords = [
        (261.63, 329.63, 392.00),
        (196.00, 246.94, 392.00),
        (220.00, 261.63, 329.63),
        (174.61, 220.00, 349.23),
    ]
    melody = [523.25, 659.25, 783.99, 659.25, 587.33, 659.25, 523.25, 493.88]
    frames = bytearray()
    total = round(DURATION * SAMPLE_RATE)
    for sample in range(total):
        t = sample / SAMPLE_RATE
        chord = chords[int(t / 2.0) % len(chords)]
        beat = int(t * 2) % len(melody)
        beat_phase = (t * 2) % 1
        envelope = math.exp(-3.2 * beat_phase)
        pad = sum(math.sin(2 * math.pi * frequency * t) for frequency in chord) / 3
        lead = math.sin(2 * math.pi * melody[beat] * t) * envelope
        bass = math.sin(2 * math.pi * (chord[0] / 2) * t)
        kick_phase = t % 0.5
        kick = math.sin(2 * math.pi * (72 - 35 * kick_phase) * t) * math.exp(-18 * kick_phase)
        fade = min(1.0, t / 1.2, (DURATION - t) / 1.8)
        value = max(-1.0, min(1.0, (0.40 * pad + 0.20 * lead + 0.22 * bass + 0.18 * kick) * fade))
        left = round(value * 13_500)
        right = round(value * 12_800)
        frames.extend(struct.pack("<hh", left, right))

    with wave.open(str(MUSIC), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def mix() -> None:
    if VOICE.stat().st_size < 10_000:
        raise SystemExit("La narration est vide ou invalide ; mixage annulé.")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    filter_graph = (
        "[1:a]volume=1.18,adelay=450|450[voice];"
        "[2:a]volume=0.13[music];"
        "[music][voice]amix=inputs=2:duration=first:dropout_transition=2[audio]"
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", str(VIDEO),
            "-i", str(VOICE),
            "-i", str(MUSIC),
            "-filter_complex", filter_graph,
            "-map", "0:v:0",
            "-map", "[audio]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(MIXED),
        ],
        check=True,
    )
    MIXED.replace(VIDEO)


if __name__ == "__main__":
    if not VOICE.exists():
        raise SystemExit(f"Narration manquante : {VOICE}")
    make_music()
    mix()
    print(f"Vidéo sonorisée : {VIDEO}")
