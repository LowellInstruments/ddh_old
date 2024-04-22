import py_cui
from scripts.script_ddc import DDC


root = py_cui.PyCUI(5, 2)
root.set_title('DDH Configuration')
_ = DDC(root)


if __name__ == "__main__":
    root.start()
