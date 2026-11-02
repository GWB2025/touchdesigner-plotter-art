"""Run inside TouchDesigner's Python Textport to build the reusable project.

exec(compile(open('/absolute/path/touchdesigner/build_project.py').read(),
             '/absolute/path/touchdesigner/build_project.py', 'exec'))
"""

from pathlib import Path

import td


def build_project(source_root):
    """Create a self-contained component without altering existing operators."""
    source_root = Path(source_root)
    if op("/nested_currents"):
        raise RuntimeError("A /nested_currents component already exists; open a fresh project to rebuild.")
    component = op("/").create(td.baseCOMP, "nested_currents")
    component.nodeX = 550
    component.nodeY = 150
    component.nodeWidth = 420
    component.nodeHeight = 300
    component.color = (0.65, 0.35, 0.15)
    page = component.appendCustomPage("Artwork")
    fields = [("Seed", "Seed", "Int", 42, 0, 2147483647),
              ("Columns", "Columns", "Int", 6, 1, 16),
              ("Rows", "Rows", "Int", 4, 1, 12),
              ("Rings", "Outlines per cell", "Int", 5, 1, 12),
              ("Rotation", "Rotation (degrees)", "Float", 28, 0, 90),
              ("Drift", "Centre drift", "Float", 0.55, 0, 1),
              ("Margin", "Margin (mm)", "Float", 8, 1, 45),
              ("Stroke", "Pen width (mm)", "Float", 0.45, 0.05, 2)]
    for name, label, kind, value, low, high in fields:
        par = getattr(page, "append" + kind)(name, label=label)[0]
        par.default = value
        par.val = value
        par.min, par.max = low, high
        par.clampMin = par.clampMax = True
        par.normMin, par.normMax = low, 1000 if name == "Seed" else high
    palette = page.appendMenu("Palette", label="Pen palette")[0]
    palette.menuNames = ["earth", "black"]
    palette.menuLabels = ["Orange / Light Brown / Dark Brown", "Black only"]
    palette.default = "earth"
    palette.val = "earth"
    page.appendPulse("Nextseed", label="Next seed")
    status = page.appendStr("Status", label="Drawing status")[0]
    status.enable = False
    export_page = component.appendCustomPage("Export")
    export_page.appendFolder("Outputfolder", label="Output folder")[0].val = "exports"
    export_page.appendPulse("Exportsvg", label="Export postcard SVG")
    export_page.appendPulse("Exportcarrier", label="Export on A4 carrier")
    export_page.appendStr("Lastfile", label="Last exported file")[0].enable = False

    for name, source in [("core", source_root / "plotter_art/core.py"),
                         ("controller", source_root / "touchdesigner/controller.py"),
                         ("sop_callbacks", source_root / "touchdesigner/sop_callbacks.py")]:
        dat = component.create(td.textDAT, name)
        dat.text = source.read_text(encoding="utf-8")
        dat.nodeX = -600
        dat.nodeY = -200 * ["core", "controller", "sop_callbacks"].index(name)

    for index in range(3):
        geo = component.create(td.geometryCOMP, f"pen{index + 1}_geometry")
        # Geometry components start with a default torus; replace only children
        # of this newly-created component.
        for child in list(geo.children):
            child.destroy()
        geo.appendCustomPage("Pen").appendInt("Penindex")[0].val = index
        lines = geo.create(td.scriptSOP, "lines")
        lines.par.callbacks = component.op("sop_callbacks")
        lines.display = lines.render = True
        material = component.create(td.constantMAT, f"pen{index + 1}_material")
        for channel, suffix in enumerate("rgb"):
            material.par["color" + suffix].expr = (
                f"op('controller').module.pen_colour(parent(), {index}, {channel})")
        material.par.wirewidth.expr = "parent().par.Stroke * 1000 / 148"
        geo.par.material = material
        geo.nodeX, geo.nodeY = -100, -index * 220
        material.nodeX, material.nodeY = -350, -index * 220

    camera = component.create(td.cameraCOMP, "camera")
    camera.par.tz = 100
    camera.par.projection = "ortho"
    camera.par.orthowidth = 148
    camera.nodeX, camera.nodeY = 150, -300
    preview = component.create(td.renderTOP, "preview")
    preview.par.camera = camera
    preview.par.geometry = "pen*_geometry"
    preview.par.lights = ""
    preview.par.bgcolorr = preview.par.bgcolorg = preview.par.bgcolorb = 1
    preview.par.bgcolora = 1
    preview.par.outputresolution = "custom"
    preview.par.resolutionw = 1000
    preview.par.resolutionh = 710
    preview.nodeX, preview.nodeY = 400, 0
    preview.nodeWidth, preview.nodeHeight = 520, 369
    output = component.create(td.nullTOP, "OUT_ARTWORK")
    output.inputConnectors[0].connect(preview)
    output.nodeX, output.nodeY = 1000, 0
    component.par.opviewer = output
    component.viewer = True
    note = component.create(td.textDAT, "START_HERE")
    note.text = ("NESTED CURRENTS / Milestone 01\n\n"
                 "Select the nested_currents component to adjust Artwork parameters.\n"
                 "Use the Export page to write a postcard SVG or an A4 carrier SVG.\n"
                 "Artwork is 148 x 105 mm; A4 carrier offset is (31, 96) mm.\n"
                 "Export at actual size. Preview and export use identical vector geometry.\n"
                 "All Python source is embedded; no pip installation is needed.\n"
                 "Screen ink colours are approximate. No plotter movement is triggered here.\n")
    note.nodeX, note.nodeY = -600, 300
    callbacks = component.create(td.parameterexecuteDAT, "controls")
    callbacks.text = (source_root / "touchdesigner/parameter_callbacks.py").read_text()
    callbacks.par.op = component
    callbacks.par.pars = "Seed Columns Rows Rings Rotation Drift Margin Stroke Palette Nextseed Exportsvg Exportcarrier"
    callbacks.par.valuechange = True
    callbacks.par.onpulse = True
    callbacks.nodeX, callbacks.nodeY = -600, -600
    component.op("controller").module.refresh(component)
    component.currentPage = component.customPages[0]
    component.save(str(source_root / "Nested_Currents.tox"))
    project.save(str(source_root / "Nested_Currents_Milestone_01.toe"))
    print("Built Nested_Currents_Milestone_01.toe and Nested_Currents.tox")
    return component


build_project(Path(__file__).resolve().parents[1])
