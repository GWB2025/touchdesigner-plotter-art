"""Embedded Script SOP callbacks: the preview uses the exact exported paths."""


def onCook(scriptOp):
    scriptOp.clear()
    component = scriptOp.parent(2)
    art = component.op("controller").module.artwork(component)
    pen_index = int(scriptOp.parent().par.Penindex)
    for path in art.paths:
        if path.pen != pen_index:
            continue
        poly = scriptOp.appendPoly(len(path.points), closed=False, addPoints=True)
        for vertex, (x, y) in zip(poly, path.points):
            vertex.point.x = x - art.settings.width_mm / 2
            vertex.point.y = art.settings.height_mm / 2 - y
            vertex.point.z = 0


def onSetupParameters(scriptOp):
    pass


def onPulse(par):
    pass
