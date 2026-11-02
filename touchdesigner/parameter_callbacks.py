"""Embedded Parameter Execute DAT callbacks."""


def onValueChange(par, prev):
    if par.name in {"Seed", "Columns", "Rows", "Rings", "Rotation", "Drift",
                    "Margin", "Stroke", "Palette"}:
        par.owner.op("controller").module.refresh(par.owner)


def onPulse(par):
    par.owner.op("controller").module.pulse(par)
