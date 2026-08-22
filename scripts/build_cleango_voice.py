"""Generate the French female CleanGo narration with a neural voice."""

import asyncio
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "apps" / "entreprises" / "static" / "entreprises" / "media" / "video" / "cleango-voix-feminine.mp3"
TEXT = (
    "Votre voiture est sale, et vous ne savez pas où aller ? Découvrez CleanGo. "
    "Depuis votre téléphone, localisez les stations de lavage les plus proches. "
    "Consultez leurs catalogues, leurs services et leurs prix, puis choisissez votre lavage. "
    "CleanGo vous indique l’itinéraire jusqu’à la station. À votre arrivée, la caissière "
    "enregistre votre nom et votre véhicule. Pendant que les professionnels prennent soin "
    "de votre voiture, détendez-vous. Payez simplement avec Wave, puis repartez satisfait. "
    "CleanGo, l’idée du lavage en un clic. Retrouvez-nous sur www point cleango point ci."
)


async def main() -> None:
    speech = edge_tts.Communicate(TEXT, "fr-FR-DeniseNeural", rate="+35%", volume="+5%")
    await speech.save(str(OUTPUT))
    print(f"Voix créée : {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
