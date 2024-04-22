import os

import py_cui
from scripts.script_ddc import DDC


if __name__ == "__main__":
    while 1:
        root = py_cui.PyCUI(7, 2)
        root.set_title('DDC')
        _ = DDC(root)
        root.start()
