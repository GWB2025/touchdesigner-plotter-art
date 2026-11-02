"""Geometry and export contracts, independent of TouchDesigner."""

import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from plotter_art.core import ArtSettings, Composition, SvgExporter

SVG = {"s": "http://www.w3.org/2000/svg"}


class GeometryTests(unittest.TestCase):
    def test_seed_reproduces_geometry_and_different_seed_changes_it(self):
        first = Composition.generate(ArtSettings(seed=42))
        second = Composition.generate(ArtSettings(seed=42))
        other = Composition.generate(ArtSettings(seed=43))
        self.assertEqual(first.paths, second.paths)
        self.assertNotEqual(first.paths, other.paths)

    def test_every_square_is_a_separate_closed_four_edge_path(self):
        art = Composition.generate(ArtSettings())
        self.assertEqual(len(art.paths), 6 * 4 * 5)
        for path in art.paths:
            self.assertEqual(len(path.points), 5)
            self.assertEqual(path.points[0], path.points[-1])
            lengths = [math.dist(a, b) for a, b in
                       zip(path.points, path.points[1:])]
            self.assertTrue(all(x > 0 for x in lengths))
            self.assertLess(max(lengths) - min(lengths), 1e-9)

    def test_extreme_controls_stay_inside_margin(self):
        for seed in range(12):
            for rows, columns in [(1, 1), (4, 6), (12, 16)]:
                settings = ArtSettings(seed=seed, rows=rows, columns=columns,
                                       rotation_deg=90, jitter=1, rings=12)
                art = Composition.generate(settings)
                for path in art.paths:
                    for x, y in path.points:
                        self.assertGreaterEqual(x, settings.margin_mm)
                        self.assertLessEqual(x, settings.width_mm-settings.margin_mm)
                        self.assertGreaterEqual(y, settings.margin_mm)
                        self.assertLessEqual(y, settings.height_mm-settings.margin_mm)

    def test_invalid_controls_fail_clearly(self):
        invalid = [{"width_mm": float("nan")}, {"height_mm": 0},
                   {"margin_mm": 60}, {"columns": 0}, {"rings": 13},
                   {"jitter": 1.1}, {"rotation_deg": float("inf")},
                   {"rows": 2.5}, {"seed": True}, {"stroke_mm": 0}]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                Composition.generate(replace(ArtSettings(), **change))

    def test_monochrome_has_one_pen_and_identical_geometry(self):
        settings = ArtSettings()
        colour = Composition.generate(settings)
        mono = Composition.generate(replace(settings, palette="black"))
        self.assertEqual([p.points for p in colour.paths],
                         [p.points for p in mono.paths])
        self.assertEqual(len(set(p.pen for p in mono.paths)), 1)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.art = Composition.generate(ArtSettings())
        self.exporter = SvgExporter(self.art)

    def test_svg_has_mm_page_three_layers_and_plain_unfilled_paths(self):
        root = ET.fromstring(self.exporter.render())
        self.assertEqual(root.attrib["width"], "148mm")
        self.assertEqual(root.attrib["height"], "105mm")
        self.assertEqual(root.attrib["viewBox"], "0 0 148 105")
        self.assertEqual(len(root.findall("s:g", SVG)), 3)
        paths = root.findall(".//s:path", SVG)
        self.assertEqual(len(paths), len(self.art.paths))
        for path in paths:
            self.assertEqual(path.attrib["fill"], "none")
            self.assertTrue(path.attrib["d"].endswith("Z"))
            self.assertNotIn("transform", path.attrib)
        self.assertEqual(root.findall(".//s:image", SVG), [])

    def test_metadata_recreates_byte_identical_svg(self):
        svg = self.exporter.render()
        root = ET.fromstring(svg)
        metadata = json.loads(root.find("s:metadata", SVG).text)
        regenerated = Composition.generate(ArtSettings(**metadata["settings"]))
        self.assertEqual(SvgExporter(regenerated).render(), svg)
        self.assertIn("generator_version", metadata)
        self.assertIn("geometry_sha256", metadata)

    def test_carrier_translation_is_exact_and_does_not_add_plot_marks(self):
        root = ET.fromstring(self.exporter.render(carrier=True))
        self.assertEqual(root.attrib["width"], "210mm")
        self.assertEqual(root.attrib["height"], "297mm")
        a = ET.fromstring(self.exporter.render()).find(".//s:path", SVG)
        b = root.find(".//s:path", SVG)
        def first_point(path):
            return tuple(map(float, path.attrib["d"].split()[1:3]))
        ax, ay = first_point(a)
        bx, by = first_point(b)
        self.assertAlmostEqual(bx-ax, 31, places=3)
        self.assertAlmostEqual(by-ay, 96, places=3)
        self.assertEqual(len(root.findall(".//s:path", SVG)), len(self.art.paths))

    def test_export_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.exporter.save(Path(folder), stem="example")
            second = self.exporter.save(Path(folder), stem="example")
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(), second.read_text())
            self.assertTrue(first.with_suffix(".json").is_file())


if __name__ == "__main__":
    unittest.main()
