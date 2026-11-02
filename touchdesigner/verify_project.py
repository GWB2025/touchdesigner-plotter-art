"""Run inside TouchDesigner to check the real SOPs and SVG export."""

import json
import math
from pathlib import Path


def verify(component):
    controller = component.op("controller").module
    art = controller.artwork(component)
    for pen_index in range(3):
        sop = component.op(f"pen{pen_index + 1}_geometry/lines")
        sop.cook(force=True)
        expected = [p for p in art.paths if p.pen == pen_index]
        assert len(sop.prims) == len(expected)
        for primitive, path in zip(sop.prims, expected):
            assert len(primitive) == len(path.points)
            for vertex, (x, y) in zip(primitive, path.points):
                assert math.isclose(vertex.point.x, x - 74, abs_tol=1e-4)
                assert math.isclose(vertex.point.y, 52.5 - y, abs_tol=1e-4)
    assert not component.errors(recurse=True), component.errors(recurse=True)
    return art.geometry_sha256


component = op("/nested_currents")
controller = component.op("controller").module
component.par.Seed = 42
component.par.Palette = "earth"
controller.refresh(component)
first = verify(component)
component.par.Seed = 137
controller.refresh(component)
assert verify(component) != first
component.par.Seed = 42
controller.refresh(component)
assert verify(component) == first
component.par.Palette = "black"
controller.refresh(component)
verify(component)
component.par.Palette = "earth"
controller.refresh(component)
root = Path(project.folder)
svg_path = controller.export(component)
assert svg_path.read_text() == component.op("core").module.SvgExporter(
    controller.artwork(component)).render()
carrier_path = controller.export(component, carrier=True)
component.op("preview").save(str(root / "docs/preview.png"))
result = {"touchdesigner_version": str(app.version),
          "touchdesigner_build": str(app.build),
          "checks": {"sop_coordinates_match_export": True,
                     "seed_change_and_restore": True,
                     "monochrome_geometry": True,
                     "native_svg_export": True,
                     "native_carrier_export": True,
                     "recursive_operator_errors": []},
          "svg": svg_path.name, "carrier_svg": carrier_path.name,
          "statistics": controller.artwork(component).statistics,
          "geometry_sha256": first}
(root / "docs/touchdesigner-verification.json").write_text(
    json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
