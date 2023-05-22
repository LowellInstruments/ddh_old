import glob
import os
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QApplication
import pyqtgraph as pg


class SeparateGraphWindow(QtWidgets.QMainWindow):

    def _check_graph_req_file_at_boot(self):
        rv = 0
        try:
            # file written by DDH plot request
            with open('/tmp/graph_req.json') as f:
                self.fol = f.read().strip()
            if not os.path.exists(self.fol):
                print('graph: error _at_boot, bad_fol {}'.format(self.fol))
                os._exit(1)
            return self.fol
        except (Exception, ) as ex:
            print('graph: error _at_boot, exception', ex)
            os._exit(1)

    @staticmethod
    def _graph_infer_folder_logger_metric(path):
        ff_t = glob.glob("{}/{}".format(path, "*_Temperature.csv"))
        ff_p = glob.glob("{}/{}".format(path, "*_Pressure.csv"))
        ff_do = glob.glob("{}/{}".format(path, "*_DissolvedOxygen.csv"))
        if ff_do and (ff_t or ff_p):
            print('graph: error mixed files in ')
            os._exit(1)
        if ff_t:
            return "_Temperature.csv"
        if ff_do:
            return "_DissolvedOxygen.csv"

    def _btn_close_click(self):
        print('closing graph window')
        self.close()

    def _btn_next_logger_click(self):
        self.g.setTitle("next logger", color="b", size="15pt")
        print('next_logger')

    def _btn_next_span_click(self):
        print('next_span')

    def _graph_line(self, x, y, plotname, color):
        pen = pg.mkPen(color=color)
        self.g.plot(x, y,
                    name=plotname,
                    pen=pen,
                    symbol='+',
                    symbolSize=10,
                    symbolBrush=color)

    def __init__(self, *args, **kwargs):
        super(SeparateGraphWindow, self).__init__(*args, **kwargs)

        # grab folder to plot
        self.fol_ls = self._get_list_of_all_mac_folders()
        self.fol = self._check_graph_req_file_at_boot()
        self.met = self._graph_infer_folder_logger_metric(self.fol)

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
        self.g.setBackground('w')

        # plot the data
        self.g.setTitle("Your Title Here", color="b", size="15pt")
        styles = {"color": "#f00", "font-size": "20px"}
        self.g.setLabel("left", "Temperature (°C)", **styles)
        self.g.setLabel("bottom", "Hour (H)", **styles)
        self.g.addLegend()
        self.g.showGrid(x=True, y=True)
        hour = [1,2,3,4,5,6,7,8,9,10]
        temperature_1 = [30,32,34,32,33,31,29,32,35,45]
        temperature_2 = [50,35,44,22,38,32,27,38,32,44]
        self.g.setXRange(0, 10, padding=0)
        self.g.setYRange(20, 55, padding=0)
        self._graph_line(hour, temperature_1, "Sensor1", 'r')
        self._graph_line(hour, temperature_2, "Sensor2", 'b')


# to test
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SeparateGraphWindow()
    ex.show()
    sys.exit(app.exec_())
