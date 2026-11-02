"""Embedded Text DAT module linking custom controls to the tested core."""

from pathlib import Path


def settings(component):
    p = component.par
    core = component.op("core").module
    return core.ArtSettings(seed=int(p.Seed), columns=int(p.Columns),
                            rows=int(p.Rows), rings=int(p.Rings),
                            rotation_deg=float(p.Rotation), jitter=float(p.Drift),
                            margin_mm=float(p.Margin), stroke_mm=float(p.Stroke),
                            palette=p.Palette.eval())


def artwork(component):
    core = component.op("core").module
    return core.Composition.generate(settings(component))


def pen_colour(component, pen_index, channel):
    core = component.op("core").module
    pens = core.PALETTES[component.par.Palette.eval()]
    colour = pens[min(pen_index, len(pens) - 1)].colour
    return int(colour[1 + 2 * channel:3 + 2 * channel], 16) / 255


def refresh(component):
    try:
        art = artwork(component)
        for geometry in component.ops("pen*_geometry"):
            geometry.op("lines").cook(force=True)
        stats = art.statistics
        component.par.Status = (f"{stats['paths']} outlines | "
                                f"{stats['drawing_length_mm']/1000:.2f} m | "
                                f"{stats['pen_colours']} pens")
        component.op("preview").cook(force=True)
    except Exception as error:
        component.par.Status = "Error: " + str(error)
        raise


def export(component, carrier=False):
    try:
        core = component.op("core").module
        folder = Path(component.par.Outputfolder.eval()).expanduser()
        if not folder.is_absolute():
            folder = Path(project.folder) / folder
        path = core.SvgExporter(artwork(component)).save(folder, carrier=carrier)
        component.par.Lastfile = str(path)
        component.par.Status = "Saved " + path.name
        return path
    except Exception as error:
        component.par.Status = "Export failed: " + str(error)
        raise


def pulse(par):
    component = par.owner
    if par.name == "Nextseed":
        component.par.Seed = (int(component.par.Seed) + 1) % 2147483648
        refresh(component)
    elif par.name == "Exportsvg":
        export(component)
    elif par.name == "Exportcarrier":
        export(component, carrier=True)
