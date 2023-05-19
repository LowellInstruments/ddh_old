import os
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QApplication
import pyqtgraph as pg


class SeparateGraphWindow(QtWidgets.QMainWindow):

    def _btn_close_click(self):
        print('closing graph window')
        self.close()

    def _btn_next_logger_click(self):
        self.g.setTitle("next logger", color="b", size="15pt")
        print('next_logger')

    def _btn_next_span_click(self):
        print('next_span')

    def _check(self):
        if not self.fol_ls:
            self.g.setTitle("error: empty folder list", color="r", size="15pt")
        # todo: do folder setting on pressing 1 and on auto-download
        fol = self.fol_ls[0]

    def _plot_line(self, x, y, plotname, color):
        pen = pg.mkPen(color=color)
        self.g.plot(x, y,
                    name=plotname,
                    pen=pen,
                    symbol='+',
                    symbolSize=10,
                    symbolBrush=color)

    def __init__(self, *args, **kwargs):
        super(SeparateGraphWindow, self).__init__(*args, **kwargs)

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

        # debug: variables
        self.span = 'h'
        self.fol_ls = [f.path for f in os.scandir('../dl_files') if f.is_dir()]
        self.fol_ls = [f for f in self.fol_ls if "ddh" not in f]

        # check everything all right
        if not self._check():
            return

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
        self._plot_line(hour, temperature_1, "Sensor1", 'r')
        self._plot_line(hour, temperature_2, "Sensor2", 'b')


# to test
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SeparateGraphWindow()
    ex.show()
    sys.exit(app.exec_())
