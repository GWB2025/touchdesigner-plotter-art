"""Pure geometry and SVG export; standard library only, Python 3.11+."""

import hashlib
import json
import math
import random
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

VERSION = "0.1.0"
SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
ET.register_namespace("", SVG_NS)
ET.register_namespace("inkscape", INKSCAPE_NS)


@dataclass(frozen=True)
class Pen:
    """A named pen with an approximate screen colour."""

    name: str
    colour: str


PALETTES = {
    "earth": (Pen("Orange", "#df7b28"), Pen("Light Brown", "#a97850"),
              Pen("Dark Brown", "#493126")),
    "black": (Pen("Black", "#222222"),),
}


@dataclass(frozen=True)
class ArtSettings:
    """All inputs needed to reproduce a Nested Currents composition."""

    seed: int = 42
    width_mm: float = 148
    height_mm: float = 105
    margin_mm: float = 8
    columns: int = 6
    rows: int = 4
    rings: int = 5
    rotation_deg: float = 28
    jitter: float = 0.55
    stroke_mm: float = 0.45
    palette: str = "earth"

    def validate(self):
        """Reject invalid or excessive inputs before generating geometry."""
        for name, low, high in [("seed", 0, 2147483647), ("columns", 1, 16),
                                ("rows", 1, 12), ("rings", 1, 12)]:
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer from {low} to {high}.")
        for name, low, high in [("width_mm", 20, 210), ("height_mm", 20, 297),
                                ("margin_mm", 1, 50), ("rotation_deg", 0, 90),
                                ("jitter", 0, 1), ("stroke_mm", 0.05, 2)]:
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not low <= value <= high):
                raise ValueError(f"{name} must be finite and from {low} to {high}.")
        if 2 * self.margin_mm >= min(self.width_mm, self.height_mm):
            raise ValueError("Margins leave no drawable page area.")
        if self.palette not in PALETTES:
            raise ValueError("Choose the earth or black palette.")


@dataclass(frozen=True)
class PlotPath:
    """One continuous pen stroke, including the closing point."""

    points: tuple
    pen: int

    @property
    def length_mm(self):
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))


@dataclass(frozen=True)
class Composition:
    """Immutable art geometry in page coordinates: x right, y down, mm."""

    settings: ArtSettings
    paths: tuple

    @classmethod
    def generate(cls, settings):
        settings.validate()
        rng = random.Random(settings.seed)
        cell_w = (settings.width_mm - 2 * settings.margin_mm) / settings.columns
        cell_h = (settings.height_mm - 2 * settings.margin_mm) / settings.rows
        cell = min(cell_w, cell_h)
        # The circumscribed circle plus maximum centre drift fits within
        # 46% of the cell width, even at maximum rotation and jitter.
        half = cell * 0.40 / math.sqrt(2)
        pen_count = len(PALETTES[settings.palette])
        paths = []
        for row in range(settings.rows):
            for col in range(settings.columns):
                cx = settings.margin_mm + (col + 0.5) * cell_w
                cy = settings.margin_mm + (row + 0.5) * cell_h
                dx = (rng.random() * 2 - 1) * cell * 0.04 * settings.jitter
                dy = (rng.random() * 2 - 1) * cell * 0.04 * settings.jitter
                phase = rng.random() * math.tau
                direction = -1 if rng.random() < 0.5 else 1
                for ring in range(settings.rings):
                    t = ring / max(1, settings.rings - 1)
                    radius = half * (1 - 0.78 * t)
                    angle = math.radians(settings.rotation_deg) * (
                        0.35 * math.sin(phase + col * 0.45 + row * 0.6)
                        + direction * t * 0.7)
                    co, si = math.cos(angle), math.sin(angle)
                    points = tuple((cx + dx * t + x * co - y * si,
                                    cy + dy * t + x * si + y * co)
                                   for x, y in [(-radius, -radius),
                                                (radius, -radius),
                                                (radius, radius),
                                                (-radius, radius)])
                    paths.append(PlotPath(points + (points[0],),
                                          (col + row + ring) % pen_count))
        return cls(settings, tuple(paths))

    @property
    def pens(self):
        return PALETTES[self.settings.palette]

    @property
    def geometry_sha256(self):
        value = [(p.pen, [[round(x, 6), round(y, 6)] for x, y in p.points])
                 for p in self.paths]
        return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()

    @property
    def statistics(self):
        return {"paths": len(self.paths), "segments": 4 * len(self.paths),
                "pen_colours": len(self.pens),
                "drawing_length_mm": round(sum(p.length_mm for p in self.paths), 2)}


class SvgExporter:
    """Write flattened, colour-grouped SVGs accepted by SVG Plotter."""

    def __init__(self, composition):
        self.art = composition

    def metadata(self, carrier=False):
        s = self.art.settings
        if carrier and (s.width_mm != 148 or s.height_mm != 105):
            raise ValueError("The A4 carrier placement requires a 148 x 105 mm postcard.")
        return {"title": "Nested Currents", "generator": "TouchDesigner Plotter Art",
                "generator_version": VERSION, "settings": asdict(s),
                "geometry_sha256": self.art.geometry_sha256,
                "statistics": self.art.statistics,
                "placement": {"page_mm": [210, 297] if carrier else [s.width_mm, s.height_mm],
                              "offset_mm": [31, 96] if carrier else [0, 0]},
                "pens": [asdict(p) for p in self.art.pens],
                "colour_note": "Screen colours are illustrative, not measured ink matches."}

    def render(self, carrier=False):
        info = self.metadata(carrier)
        width, height = info["placement"]["page_mm"]
        ox, oy = info["placement"]["offset_mm"]
        tag = lambda name: "{" + SVG_NS + "}" + name
        root = ET.Element(tag("svg"), {"width": f"{width:g}mm",
                                      "height": f"{height:g}mm",
                                      "viewBox": f"0 0 {width:g} {height:g}",
                                      "version": "1.1"})
        ET.SubElement(root, tag("title")).text = "Nested Currents"
        ET.SubElement(root, tag("desc")).text = (
            "Seeded nested squares. Separate pen strokes; physical dimensions in mm. "
            "Import at actual size. No background, border or registration marks are plotted.")
        ET.SubElement(root, tag("metadata")).text = json.dumps(info, sort_keys=True)
        for index, pen in enumerate(self.art.pens):
            group = ET.SubElement(root, tag("g"), {
                "id": f"pen-{index + 1}-{pen.name.lower().replace(' ', '-')}",
                "{" + INKSCAPE_NS + "}groupmode": "layer",
                "{" + INKSCAPE_NS + "}label": f"{index + 1}: {pen.name}",
                "fill": "none", "stroke": pen.colour})
            for path in self.art.paths:
                if path.pen != index:
                    continue
                data = " ".join(f"{'M' if i == 0 else 'L'} {x+ox:.4f} {y+oy:.4f}"
                                for i, (x, y) in enumerate(path.points[:-1])) + " Z"
                ET.SubElement(group, tag("path"), {
                    "d": data, "fill": "none", "stroke": pen.colour,
                    "stroke-width": f"{self.art.settings.stroke_mm:g}",
                    "stroke-linecap": "round", "stroke-linejoin": "round"})
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode") + "\n"

    def save(self, folder, stem=None, carrier=False):
        """Preserve previous exports and save a matching reproducibility record."""
        svg = self.render(carrier)
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        stem = stem or f"nested-currents-seed-{self.art.settings.seed}"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", stem):
            raise ValueError("Export name may contain letters, digits, hyphens and underscores.")
        base = stem + ("-a4-carrier" if carrier else "")
        suffix = 0
        while True:
            name = base if suffix == 0 else f"{base}-{suffix:03d}"
            svg_path = folder / (name + ".svg")
            json_path = folder / (name + ".json")
            if svg_path.exists() or json_path.exists():
                suffix += 1
                continue
            try:
                with svg_path.open("x", encoding="utf-8") as stream:
                    stream.write(svg)
            except FileExistsError:
                suffix += 1
                continue
            with json_path.open("x", encoding="utf-8") as stream:
                json.dump(self.metadata(carrier), stream, indent=2, sort_keys=True)
                stream.write("\n")
            return svg_path
