import glob
import os
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QApplication
import pyqtgraph as pg
from mat.utils import linux_is_rpi
import pandas as pd
import dateutil.parser as dp


_g_ff_t = []
_g_ff_p = []
_g_ff_do = []


p1 = None
p2 = None


def _graph_update_views():
    # used when resizing
    global p1, p2
    p2.setGeometry(p1.vb.sceneBoundingRect())
    p2.linkedViewChanged(p1.vb, p2.XAxis)


def _graph_get_mac_folder_list():
    """
    return absolute paths of "dl_files/<mac>" folders
    """
    d = '/home/pi/ddh/dl_files'
    if not linux_is_rpi():
        d = '/home/kaz/PycharmProjects/ddh/dl_files'

    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        # remove 'ddh_vessel' folders
        return [f for f in f_l if "ddh" not in os.path.basename(f)]
    return []


class SeparateGraphWindow(QtWidgets.QMainWindow):

    def _btn_close_click(self):
        print('closing graph window')
        self.close()

    def _btn_next_logger_click(self):
        self.g.setTitle("next logger", color="b", size="15pt")
        print('next_logger')

    def _btn_next_span_click(self):
        print('next_span')
        # example how to update graph
        p1.clear()
        p2.clear()
        self.graph_all(inv=True)

    def __init__(self, *args, **kwargs):
        super(SeparateGraphWindow, self).__init__(*args, **kwargs)

        # our variables
        self.fol_ls = _graph_get_mac_folder_list()
        if not self.fol_ls:
            return
        self.fol_ls_len = len(self.fol_ls)
        self.fol = _graph_get_fol_file_at_boot()
        self.fol_ls_idx = self.fol_ls.index(self.fol)
        self.met = _graph_get_folder_metric(self.fol)

        # controls
        self.btn_close = QPushButton('Quit', self)
        self.btn_next_logger = QPushButton('next logger', self)
        self.btn_next_span = QPushButton('next span', self)
        self.btn_close.clicked.connect(self._btn_close_click)
        self.btn_next_logger.clicked.connect(self._btn_next_logger_click)
        self.btn_next_span.clicked.connect(self._btn_next_span_click)
        self.g = pg.PlotWidget()

        # layout everything
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.btn_close)
        hl.addWidget(self.btn_next_logger)
        hl.addWidget(self.btn_next_span)
        vl = QtWidgets.QVBoxLayout()
        vl.setSpacing(10)
        vl.addLayout(hl)
        vl.addWidget(self.g)
        wid.setLayout(vl)
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
        _graph_update_views()
        p1.vb.sigResized.connect(_graph_update_views)
        p1.setLabel("left", "Temperature (°C)",
                    **{"color": "#f00", "font-size": "20px"})
        p1.getAxis('right').setLabel("PRESSURE",
                    **{"color": "blue", "font-size": "20px"})

        data = _graph_get_data_()
        x = data['ISO 8601 Time']
        t = data['Temperature (C)']
        p = data['Pressure (dbar)']
        if inv:
            t, p = p, t
        p1.setYRange(0, 100, padding=0)
        p2.setYRange(0, 20, padding=0)
        self.g.setBackground('w')
        p1.plot(x, t, pen='r')
        pi = pg.PlotCurveItem(x, p, pen='b')
        p2.addItem(pi)


def _graph_get_folder_metric(path):
    global _g_ff_t
    global _g_ff_p
    global _g_ff_do
    _g_ff_t = sorted(glob.glob("{}/{}".format(path, "*_Temperature.csv")))
    _g_ff_p = sorted(glob.glob("{}/{}".format(path, "*_Pressure.csv")))
    _g_ff_do = sorted(glob.glob("{}/{}".format(path, "*_DissolvedOxygen.csv")))
    if _g_ff_do and (_g_ff_t or _g_ff_p):
        print('graph: error mixed files in ')
        os._exit(1)
    if _g_ff_t:
        return "TP"
    if _g_ff_do:
        return "DO"


def _graph_get_fol_file_at_boot():
    """
    read file in /tmp containing folder to graph
    """
    try:
        # file written by DDH plot request
        with open('/tmp/graph_req.json') as f:
            fol = f.read().strip()
        if not os.path.exists(fol):
            print('graph: error _at_boot, bad_fol {}'.format(fol))
            os._exit(1)
        return fol
    except (Exception, ) as ex:
        print('graph: error _at_boot, exception', ex)
        os._exit(1)


def _graph_get_data_() -> dict:
    met = "TP"
    fol = "/home/kaz/PycharmProjects/ddh/dl_files/11-22-33-44-55-66"
    _g_ff_t = sorted(glob.glob("{}/{}".format(fol, "*_Temperature.csv")))
    _g_ff_p = sorted(glob.glob("{}/{}".format(fol, "*_Pressure.csv")))
    _g_ff_do = sorted(glob.glob("{}/{}".format(fol, "*_DissolvedOxygen.csv")))
    print('graph: trying met {} fol {}'.format(met, fol))
    t, p, x = [], [], []
    if met == 'TP':
        for f in _g_ff_t:
            print('loading file', f)
            df = pd.read_csv(f)
            x += list(df['ISO 8601 Time'])
            t += list(df['Temperature (C)'])
        for f in _g_ff_p:
            print('loading file', f)
            df = pd.read_csv(f)
            p += list(df['Pressure (dbar)'])
        # convert time
        x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]
        return {'ISO 8601 Time': x,
                'Temperature (C)': t,
                'Pressure (dbar)': p}
    elif met == 'DO':
        print('hola')
    else:
        print('wtf met')
        assert False


# to test
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SeparateGraphWindow()
    ex.show()
    sys.exit(app.exec_())

    # data = _graph_get_data_()
    # graph(data)
