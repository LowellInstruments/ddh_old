from scripts.script_ddc import main_ddc
import py_cui
from py_cui.keys import *


rv = 0


class DDC:

    def __init__(self, root_window: py_cui.PyCUI):
        self.r = root_window

        # --------------------------
        # column 1, menu of commands
        # --------------------------
        self.m = self.r.add_scroll_menu(
            title='Choose command',
            row=1, column=0, row_span=3
        )
        m_ls = [
            "Item1",
            "Item2"
        ]
        self.m.add_item_list(m_ls)
        self.m.add_key_command(KEY_ENTER, command=self.menu_key_enter_cb)

        # -----------------------
        # draw column 2, summary
        # -----------------------
        self.s = self.r.add_block_label(
            title='Summary\na\nb\nc',
            row=1, column=1, row_span=3, center=False, padx=10
        )
        self.s.toggle_border()

        # -----------------------------
        # initial focus to command menu
        # -----------------------------
        self.r.move_focus(self.m)

    def menu_key_enter_cb(self):
        c = self.m.get()
        if c == 'Item1':
            self.s.set_color(py_cui.RED_ON_BLACK)
        else:
            self.s.set_color(py_cui.WHITE_ON_BLACK)
        self.s.set_title(c)


# create CUI object
root = py_cui.PyCUI(5, 2)
root.set_title('DDH Configuration')
_ = DDC(root)


if __name__ == "__main__":
    while 1:
        root.start()
        print('return value is', rv)
        input()
