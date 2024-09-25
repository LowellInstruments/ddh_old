
def dbar_to_feet(dbar):
    # 1 dbar = 3.34553 feet of water
    return dbar * 3.34553


def feet_to_fathoms(feet):
    # 1 foot = 0.166667 fathoms
    return feet * 0.166667


def dbar_to_fathoms(dbar):
    feet = dbar_to_feet(dbar)
    fath = feet_to_fathoms(feet)
    return fath
