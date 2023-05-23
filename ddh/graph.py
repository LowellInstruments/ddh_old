import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QApplication, QCheckBox
import pyqtgraph as pg
from ddh.utils_graph import graph_get_fol_req_file, \
    graph_get_fol_list, graph_get_all_data_csv


p1 = None
p2 = None


def graph_update_views():
    # used when resizing
    global p1, p2
    p2.setGeometry(p1.vb.sceneBoundingRect())
    p2.linkedViewChanged(p1.vb, p2.XAxis)


class SeparateGraphWindow(QtWidgets.QMainWindow):

    def _btn_close_click(self):
        print('closing graph window')
        self.close()

    def _btn_next_logger_click(self):
        self.g.setTitle("next logger", color="b", size="15pt")
        print('next_logger')

    def _btn_cbox_lh_click(self):
        self.lh = not self.lh

    def _btn_next_span_click(self):
        print('next_span')
        # example how to update graph
        p1.clear()
        p2.clear()
        self.graph_all(inv=True)

    def __init__(self, *args, **kwargs):
        super(SeparateGraphWindow, self).__init__(*args, **kwargs)

        # ---------------------------------------
        # get requested folder and list of them
        # ---------------------------------------
        self.lh = True
        self.fol = graph_get_fol_req_file()
        if not self.fol:
            print('graph: error self.fol empty')
            return
        self.fol_ls = graph_get_fol_list()
        if not self.fol_ls:
            print('graph: no plot folders')
            return
        self.fol_ls_len = len(self.fol_ls)
        self.fol_ls_idx = self.fol_ls.index(self.fol)

        # controls
        self.btn_close = QPushButton('Quit', self)
        self.btn_cbox_lh = QCheckBox('last haul', self)
        self.btn_cbox_lh.setChecked(self.lh)
        self.btn_next_logger = QPushButton('next logger', self)
        self.btn_next_span = QPushButton('next span', self)
        self.btn_close.clicked.connect(self._btn_close_click)
        self.btn_next_logger.clicked.connect(self._btn_next_logger_click)
        self.btn_next_span.clicked.connect(self._btn_next_span_click)
        self.btn_cbox_lh.stateChanged.connect(self._btn_cbox_lh_click)
        self.g = pg.PlotWidget()

        # layout everything
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.btn_close)
        hl.addWidget(self.btn_cbox_lh)
        hl.addWidget(self.btn_next_logger)
        hl.addWidget(self.btn_next_span)
        vl = QtWidgets.QVBoxLayout()
        vl.setSpacing(10)
        vl.addLayout(hl)
        vl.addWidget(self.g)
        wid.setLayout(vl)

        # ------------------
        # draw graph at boot
        # ------------------
        self.graph_all()

    def graph_all(self, inv=False):
        global p1
        global p2
        p1 = self.g.plotItem

        # create the 2nd plot
        p2 = pg.ViewBox()
        p1.showAxis('right')
        p1.scene().addItem(p2)
        p1.getAxis('right').linkToView(p2)
        p2.setXLink(p1)
        graph_update_views()
        p1.vb.sigResized.connect(graph_update_views)
        sty = {"color": "red", "font-size": "20px"}
        p1.setLabel("left", "Temperature (°C)", **sty)
        sty = {"color": "blue", "font-size": "20px"}
        p1.getAxis('right').setLabel("Pressure (dbar)", ** sty)

        # ----------------------------------------
        # grab all this CSV data for this folder
        # ----------------------------------------
        data = graph_get_all_data_csv(self.fol, self.lh)
        if not data:
            return
        x = data['ISO 8601 Time']
        t = data['Temperature (C)']
        p = data['Pressure (dbar)']
        if inv:
            t, p = p, t

        # --------
        # draw it
        # --------
        p1.setYRange(min(t), max(t), padding=0)
        p2.setYRange(min(p), max(p), padding=0)
        self.g.setBackground('w')
        p1.plot(x, t, pen='r')
        pi = pg.PlotCurveItem(x, p, pen='b')
        p2.addItem(pi)


# to test
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SeparateGraphWindow()
    ex.show()
    sys.exit(app.exec_())
