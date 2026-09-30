"""Build static/assets/fonts/catalog.json from the Google Fonts metadata.

Usage:
    curl -s -o gf.json https://fonts.google.com/metadata/fonts
    py -3.14 scripts/build_font_catalog.py gf.json

Only names, categories and weights are stored; the fonts themselves load from the
Google Fonts CDN in the browser (tiles fetch just the letters of "ShowcaseMaker").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "static" / "assets" / "fonts" / "catalog.json"

THEMES = {
    "gaming": """Press Start 2P, VT323, Silkscreen, Pixelify Sans, Bungee, Bungee Shade, Bungee Inline, Bungee Hairline,
        Bungee Outline, Bungee Spice, Bungee Tint, Orbitron, Audiowide, Russo One, Black Ops One, Wallpoet, Monoton, Tilt Warp,
        Tilt Neon, Tilt Prism, Micro 5, Tiny5, Jersey 10, Jersey 15, Jersey 20, Jersey 25, Sixtyfour, Workbench, Bytesized,
        Handjet, Kode Mono, Oxanium, Exo 2, Rajdhani, Chakra Petch, Share Tech Mono, Iceland, Syncopate, Michroma, Zen Dots,
        Goldman, Stalinist One, Aldrich, Electrolize, Quantico, Turret Road, Major Mono Display, Nova Square, Gugi, Sarpanch,
        Teko, Bruno Ace, Bruno Ace SC, Faster One, Racing Sans One, Righteous, DotGothic16, Coda, Play, Saira Stencil One,
        Big Shoulders Stencil Display, Geostar, Geostar Fill, Audiowide, Orbitron, Jura, Unbounded, Rubik Mono One, Bungee""",
    "horror": """Creepster, Nosifer, Butcherman, Eater, Frijole, Metal Mania, Rubik Wet Paint, Rubik Glitch, Rubik Burned,
        Rubik Microbe, Rubik Distressed, Rubik Maze, Rubik Beastly, Rubik Moonrocks, Rubik Dirt, Rubik Vinyl, Jolly Lodger,
        Freckle Face, Griffy, Sedgwick Ave Display, Ewert, New Rocker, Special Elite, Fascinate, Metal, Piedra, Flavors,
        Trade Winds, Henny Penny, Rye, Ribeye Marrow, Butterfly Kids, Emblema One, Nosifer, Irish Grover, Bangers, Bahianita""",
    "gothic": """UnifrakturMaguntia, UnifrakturCook, Pirata One, Grenze Gotisch, Jacquard 12, Jacquard 24, Jacquarda Bastarda 9,
        Germania One, New Rocker, Metamorphous, MedievalSharp, Almendra Display, Almendra, Almendra SC, Fruktur, Texturina,
        Grenze, Cinzel Decorative, IM Fell English, IM Fell DW Pica, IM Fell English SC, Uncial Antiqua, Macondo,
        Macondo Swash Caps, Eagle Lake, Berkshire Swash, Amarante, Aladin, Kings, Cinzel, Old Standard TT, Luxurious Roman""",
    "cute": """Fredoka, Baloo 2, Chewy, Sniglet, Bubblegum Sans, Comic Neue, Gochi Hand, Mochiy Pop One, Mochiy Pop P One,
        Cherry Bomb One, Mogra, Grandstander, Chicle, Coiny, DynaPuff, Rammetto One, Sour Gummy, Madimi One, Delicious Handrawn,
        Nunito, Varela Round, Quicksand, Comfortaa, Kavoon, Lilita One, Luckiest Guy, Titan One, Bagel Fat One, Rampart One,
        Yusei Magic, Potta One, Kosugi Maru, M PLUS Rounded 1c, Chango, Bowlby One, Bowlby One SC, Paytone One, Shrikhand,
        Modak, Sniglet, Baloo Bhai 2, Fredoka One, Gluten, Short Stack, Patrick Hand, Neucha""",
    "poster": """Bebas Neue, Anton, Oswald, League Gothic, Six Caps, Big Shoulders Display, Antonio, Teko, Fjalla One,
        Pathway Gothic One, Archivo Black, Archivo Narrow, Barlow Condensed, Saira Condensed, Roboto Condensed,
        Sofia Sans Extra Condensed, Smooch Sans, Alumni Sans, Alfa Slab One, Abril Fatface, Ultra, Black Han Sans,
        Staatliches, Squada One, Passion One, Francois One, Yanone Kaffeesatz, Mohave, Khand, Oswald, Russo One, Arsenal""",
    "elegant": """Cinzel, Playfair Display, Cormorant, Cormorant Garamond, Marcellus, Italiana, Bodoni Moda, Great Vibes,
        Parisienne, Pinyon Script, Allura, Tangerine, Italianno, Monsieur La Doulaise, Rouge Script, Imperial Script, Ballet,
        Cormorant Infant, Libre Caslon Display, Forum, Poiret One, Josefin Sans, Philosopher, Tenor Sans, Gilda Display, Prata,
        Yeseva One, Della Respira, Federo, Julius Sans One, Limelight, Lustria, Rozha One, Cormorant SC, Marcellus SC""",
}
SCRIPT_WORDS = ("script", "brush", "calligraph", "signature", "swash")
SCRIPT_NAMES = {"Pacifico", "Dancing Script", "Great Vibes", "Sacramento", "Satisfy", "Yellowtail", "Kaushan Script", "Lobster",
                "Lobster Two", "Cookie", "Courgette", "Marck Script", "Alex Brush", "Arizonia", "Allura", "Parisienne", "Mr Dafoe",
                "Norican", "Damion", "Leckerli One", "Pattaya", "Bad Script", "Tangerine", "Italianno", "Pinyon Script", "Rochester",
                "Clicker Script", "Herr Von Muellerhoff", "Petit Formal Script", "Style Script", "Ballet", "Birthstone", "Corinthia"}
CATEGORY = {"Sans Serif": "sans", "Serif": "serif", "Display": "display", "Handwriting": "handwriting", "Monospace": "mono"}


def names(block: str) -> set[str]:
    return {name.strip() for name in block.replace("\n", ",").split(",") if name.strip()}


def build(meta_path: Path) -> dict:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    themes = {key: names(value) for key, value in THEMES.items()}
    rows = []
    for family in sorted(meta["familyMetadataList"], key=lambda f: f.get("defaultSort", 10**6)):
        subsets = family.get("subsets", [])
        if family.get("isNoto") or "latin" not in subsets or "Symbols" in family.get("classifications", []):
            continue
        if family.get("primaryScript") not in ("", None, "Latn", "Cyrl"):
            continue
        name = family["family"]
        category = CATEGORY.get(family.get("category"), "display")
        tags = [key for key, members in themes.items() if name in members]
        if category == "handwriting" and (name in SCRIPT_NAMES or any(w in name.lower() for w in SCRIPT_WORDS)):
            tags.append("script")
        elif name in SCRIPT_NAMES:
            tags.append("script")
        weights = sorted({int(k.rstrip("i")) for k in family.get("fonts", {}) if k.rstrip("i").isdigit()}) or [400]
        rows.append([name, category, 1 if "cyrillic" in subsets else 0, weights, tags])
    return {"v": 1, "source": "Google Fonts", "fonts": rows}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    data = build(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    counts = {}
    for row in data["fonts"]:
        for tag in row[4] + [row[1]] + (["cyrillic"] if row[2] else []):
            counts[tag] = counts.get(tag, 0) + 1
    print(len(data["fonts"]), "fonts ->", OUT.name, counts, round(OUT.stat().st_size / 1024), "KB")
