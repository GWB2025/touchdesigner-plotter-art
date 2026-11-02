"""Generate SVGs without launching TouchDesigner."""

import argparse
import json
from pathlib import Path

from .core import ArtSettings, Composition, SvgExporter


def main():
    parser = argparse.ArgumentParser(description="Generate Nested Currents SVG artwork.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--rings", type=int, default=5)
    parser.add_argument("--rotation", type=float, default=28)
    parser.add_argument("--jitter", type=float, default=0.55)
    parser.add_argument("--palette", choices=["earth", "black"], default="earth")
    parser.add_argument("--output", type=Path, default=Path("exports"))
    parser.add_argument("--settings", type=Path, help="Load settings from an exported JSON record.")
    parser.add_argument("--carrier", action="store_true", help="Place postcard at (31,96) mm on A4.")
    args = parser.parse_args()
    try:
        if args.settings:
            settings = ArtSettings(**json.loads(args.settings.read_text())["settings"])
        else:
            settings = ArtSettings(seed=args.seed, columns=args.columns, rows=args.rows,
                                   rings=args.rings, rotation_deg=args.rotation,
                                   jitter=args.jitter, palette=args.palette)
        art = Composition.generate(settings)
        print(SvgExporter(art).save(args.output, carrier=args.carrier))
        print(json.dumps(art.statistics))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
