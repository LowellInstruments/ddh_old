import math
import multiprocessing
import sys
import time
from datetime import datetime
from glob import glob
from math import ceil
from multiprocessing import Process
from statistics import mean

import numpy as np
import pyqtgraph as pg
import setproctitle
from PyQt5 import QtCore
from PyQt5.QtCore import QCoreApplication
from pyqtgraph import LinearRegionItem
from pyqtgraph.Qt import QtGui

from ddh.utils_graph import (utils_graph_read_fol_req_file,
                             utils_graph_get_abs_fol_list, process_graph_csv_data,
                             utils_graph_does_exist_fol_req_file,
                             utils_graph_delete_fol_req_file, utils_graph_detect_this_file_has_fast_mode,
                             utils_graph_tdo_classify_files_fast_mode)
from dds.timecache import is_it_time_to
from mat.linux import linux_is_process_running
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_cfg_logger_mac_from_sn
from utils.ddh_shared import (get_dl_folder_path_from_mac,
                              get_number_of_hauls, STATE_DDS_BLE_DOWNLOAD_STATISTICS,
                              send_ddh_udp_gui as _u)
from utils.logs import lg_gra as lg
from utils.mavg import get_interesting_idx_ma

# to be able to zoom in RPi
pg.setConfigOption('leftButtonPan', False)


# plot objects
p1 = None
p2 = None
just_booted = True

# this one is dynamic so it needs a backup
p3 = None
p3_bak = None


def _percentile(data, perc: int):
    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]


def gfm_serve():
    # ---------------------------------------
    # GFM: graph fast mode
    # only graphs files with fast mode data
    # ---------------------------------------
    _P_ = "dds_gfm"

    def _gfm_serve():
        setproctitle.setproctitle(_P_)
        try:
            utils_graph_tdo_classify_files_fast_mode()
        except (Exception, ) as ex:
            lg.a(f'error: gfm_serve -> ex {ex}')
        # instead of return prevents zombie processes
        sys.exit(0)

    # useful to remove past zombie processes
    multiprocessing.active_children()
    if linux_is_process_running(_P_):
        lg.a(f"error: seems last {_P_} took a long time")
    else:
        s = f'launching {_P_}'
        if is_it_time_to(s, 600):
            # lg.a(s)
            p = Process(target=_gfm_serve)
            p.start()


class GraphException(Exception):
    pass


# src: https://onestopdataanalysis.com/python-outlier-detection/
def _get_outliers_indexes(data, n1, n2):
    # compute inter-percentile range
    q1, q3 = np.percentile(sorted(data), [n1, n2])
    iqr = q3 - q1
    # find lower and upper bounds
    low = q1 - (1.5 * iqr)
    hig = q3 + (1.5 * iqr)
    ls_idx = [i for i, x in enumerate(data) if x <= low or x >= hig]
    return ls_idx


def _axis_room(v: list):
    return .1 * max(v)


def _sty(color):
    return {"color": color, "font-size": "20px", "font-weight": "bold"}


def _get_color_by_label(lbl):
    # google for SVG 1.0 color names
    if 'Temperature' in lbl:
        return 'red'
    if 'Pressure' in lbl:
        return 'blue'
    if 'Depth' in lbl:
        return 'blue'
    if 'DO Concentration' in lbl:
        return 'blue'
    if 'Ax' in lbl:
        return 'limegreen'
    return 'green'


class LimitsTypeError(Exception):
    def __init__(self, err='Limits type must be type int or tuple of ints', *args, **kwargs):
        super().__init__(self, err, *args, **kwargs)


class FiniteLinearRegionItem(LinearRegionItem):
    def __init__(self, limits=None, *args, **kwargs):
        super(FiniteLinearRegionItem, self).__init__(*args, **kwargs)
        """Create a new LinearRegionItem.

            Now you can define the shading area. Enjoy!

        ==============  =====================================================================
        **Arguments:**
        limits          A tuple containing the upper and lower bounds prependicular to the orientation.
                        Or a int/float containing the lower bounds prependicular to the orientation.
                        The default value is None.
        ==============  =====================================================================
        """
        self.limit = limits

    def boundingRect(self):
        br = self.viewRect()
        rng = self.getRegion()

        # Infinite with one end close
        if isinstance(self.limit, int):
            if self.orientation in ('vertical', LinearRegionItem.Vertical):
                br.setLeft(rng[0])
                br.setRight(rng[1])
                length = br.height()
                br.setBottom(self.limit)
                br.setTop(br.top() + length * self.span[0])
            else:
                br.setTop(rng[0])
                br.setBottom(rng[1])
                length = br.width()
                br.setRight(br.left() + length * self.span[1])
                br.setLeft(self.limit)
        # Finite
        elif isinstance(self.limit, tuple):
            if self.orientation in ('vertical', LinearRegionItem.Vertical):
                br.setLeft(rng[0])
                br.setRight(rng[1])
                length = br.height()
                br.setBottom(self.limit[0])
                br.setTop(self.limit[1])
            else:
                br.setTop(rng[0])
                br.setBottom(rng[1])
                length = br.width()
                br.setRight(self.limit[1])
                br.setLeft(self.limit[0])
        elif self.limit is None:
            if self.orientation in ('vertical', LinearRegionItem.Vertical):
                br.setLeft(rng[0])
                br.setRight(rng[1])
                length = br.height()
                br.setBottom(br.top() + length * self.span[1])
                br.setTop(br.top() + length * self.span[0])
            else:
                br.setTop(rng[0])
                br.setBottom(rng[1])
                length = br.width()
                br.setRight(br.left() + length * self.span[1])
                br.setLeft(br.left() + length * self.span[0])
        else:
            raise LimitsTypeError

        br = br.normalized()
        return br


def _graph_check_mac_has_dl_files(mac, fol_ls):
    for i in fol_ls:
        if mac.lower() in i.lower():
            return True
    return False


def _graph_update_views():
    # used when resizing
    global p1, p2, p3
    # for the second line
    p2.setGeometry(p1.vb.sceneBoundingRect())
    p2.linkedViewChanged(p1.vb, p2.XAxis)
    # for the 3+ line
    if p3:
        p3.setGeometry(p1.vb.sceneBoundingRect())
        p3.linkedViewChanged(p1.vb, p3.XAxis)


def _graph_busy_sign_show(a):
    a.lbl_graph_busy.setVisible(True)
    QCoreApplication.processEvents()


def _graph_busy_sign_hide(a):
    a.lbl_graph_busy.setVisible(False)


def _graph_collect_filenames_to_plot(fol):
    t = sorted(glob(f"{fol}/*_Temperature.csv"))
    p = sorted(glob(f"{fol}/*_Pressure.csv"))
    dox = sorted(glob(f"{fol}/*_DissolvedOxygen.csv"))
    tdo = sorted(glob(f"{fol}/*_TDO.csv"))



    # so we can use cache
    return '\n'.join(t) + '\n'.join(p) + '\n'.join(dox) + '\n'.join(tdo)


def _process_n_graph(a, r=''):

    # get graph from passed app
    g = a.g

    # benchmark this graphing function
    start_ts = time.perf_counter()

    # get list of absolute local 'dl_files/<mac>' folders
    fol_ls = utils_graph_get_abs_fol_list()
    fol: str

    # get current haul type
    _ht = a.cb_g_cycle_haul.currentText()

    # get zones on / off
    _zt = a.cb_g_paint_zones.currentText()

    # get haul idx
    if a.g_haul_idx is None:
        a.g_haul_idx = -1

    # get reason passed for graph
    if r == 'BLE':
        if not utils_graph_does_exist_fol_req_file():
            raise GraphException('error: no BLE requested folder to graph')
        fol = utils_graph_read_fol_req_file()
        lg.a('graph: selected last BLE download {}'.format(fol))
        utils_graph_delete_fol_req_file()
    else:
        # people pressing graph buttons
        sn = a.cb_g_sn.currentText()
        if not sn:
            raise GraphException('no one asked for a graph?')
        if sn.startswith('SN'):
            sn = sn[2:]
        mac = dds_get_cfg_logger_mac_from_sn(sn).replace(':', '-')
        if not _graph_check_mac_has_dl_files(mac, fol_ls):
            raise GraphException(f'error: no files for sn {sn} mac {mac}')
        lg.a(f'selected dropdown sn {sn} / mac {mac}')
        fol = str(get_dl_folder_path_from_mac(mac))

    # get number of hauls
    nh = get_number_of_hauls(fol)
    lg.a(f'found {nh} hauls in folder {fol}')
    if r == 'hauls_next':
        # remember this button only active on haul_text == 'single'
        if nh == 0:
            raise GraphException(f'error: no hauls for {fol}')
        a.g_haul_idx = (a.g_haul_idx - 1) % nh
        lg.a(f'button haul index = {a.g_haul_idx} / {nh}')
    if r == 'hauls_labels':
        if _ht == 'single':
            a.btn_g_next_haul.setEnabled(True)
            a.btn_g_next_haul.setVisible(True)
            a.g_haul_idx = -1
        else:
            a.btn_g_next_haul.setEnabled(False)
            a.btn_g_next_haul.setVisible(False)

    # get buttons visible or not conditionally
    a.cb_g_switch_tp.setVisible(False)

    # ----------------------------------------
    # let's CLEAR graph and start from scratch
    # ----------------------------------------
    global p1
    global p2
    global p3
    global p3_bak
    if p1:
        p1.scene().removeItem(p3_bak)
        p1.clear()
    if p2:
        p2.clear()
    if p3:
        p3.clear()
    p1 = g.plotItem

    # patch for bottom ticks, x are floats meaning timestamps
    # solves the problem of the x-axis ticks changing
    g.setAxisItems({"bottom": pg.DateAxisItem()})

    # grid or not
    g.showGrid(x=True, y=True)

    # ---------
    # 2nd line
    # ---------
    p2 = pg.ViewBox(enableMenu=True)
    p1.showAxis('right')
    p1.scene().addItem(p2)
    p1.getAxis('right').linkToView(p2)
    p2.setXLink(p1)

    # ---------
    # 3rd line
    # ---------
    tdo_graph_type = a.cb_g_switch_tp.currentText()
    if 'x-time' in tdo_graph_type:
        p3 = pg.ViewBox()
        ax3 = pg.AxisItem('right')
        p1.scene().addItem(p3)
        ax3.linkToView(p3)
        p3.setXLink(p1)
        ax3.setZValue(-10000)
        # so we can remove it later
        p3_bak = ax3
    else:
        p3_bak.setStyle(showValues=False)
        p1.scene().removeItem(p3_bak)

    # connect the thing when resizing
    _graph_update_views()
    p1.vb.sigResized.connect(_graph_update_views)

    # font: TICKS TEXT
    font = QtGui.QFont()
    font.setPixelSize(16)
    font.setBold(True)
    p1.getAxis("bottom").setStyle(tickFont=font)
    p1.getAxis("left").setStyle(tickFont=font)
    p1.getAxis("right").setStyle(tickFont=font)

    # --------------------------
    # PROCESS folder's CSV data
    # --------------------------
    data = process_graph_csv_data(fol, _ht, a.g_haul_idx)
    if not data:
        lg.a(f'warning: no data to plot in folder {fol}')
        raise GraphException(f'no data to plot')
    if 'error' in data.keys():
        raise GraphException(f'{data["error"]}')
    if 'ISO 8601 Time' not in data.keys():
        raise GraphException(f'error: no time data for {fol}')

    # x: time
    x = data['ISO 8601 Time']
    met = data['metric']

    # ----------
    # the title
    # ----------
    fmt = '%b %d %Y %H:%M'
    # choose utcfromtimestamp() / fromtimestamp()
    t1 = datetime.fromtimestamp(x[0]).strftime(fmt)
    t2 = datetime.fromtimestamp(x[-1]).strftime(fmt)
    title = '{} to {}'.format(t1, t2)

    # removed on Apr 3 2024
    # if data['pruned']:
    #     title += ' (data trimmed)'

    # --------------
    # metric labels
    # --------------
    lbl1, lbl2, lbl3 = '', '', ''
    y1, y2, y3 = [], [], []
    if met == 'TP':
        lbl1 = 'Depth (fathoms) TP'
        lbl2 = 'Temperature (F) TP'
    elif met == 'DO':
        lbl1 = 'DO Concentration (mg/l) DO'
        lbl2 = 'Temperature (F) DO'
    elif met == 'TDO':
        lbl1 = 'Depth (fathoms) TDO'
        lbl2 = 'Temperature (F) TDO'
        lbl3 = 'Ax TDO'
        y3 = data['Ax TDO']
        y4 = data['Ay TDO']
        y5 = data['Az TDO']
    y1 = data[lbl1]
    y2 = data[lbl2]

    # see if we need Depth-axis inverted
    p1.invertY('Depth' in lbl1)

    # colors
    lbl1 = lbl1.replace(' TP', '').replace(' DO', '').replace(' TDO', '')
    lbl2 = lbl2.replace(' TP', '').replace(' DO', '').replace(' TDO', '')
    lbl3 = lbl3.replace(' TP', '').replace(' DO', '').replace(' TDO', '')
    clr_1 = _get_color_by_label(lbl1)
    clr_2 = _get_color_by_label(lbl2)
    clr_3 = _get_color_by_label(lbl3)
    clr_4 = 'magenta'
    lbl1 = lbl1 + ' ─'
    lbl2 = lbl2 + ' - -'
    lbl3 = lbl3 + ' ─'
    pen1 = pg.mkPen(color=clr_1, width=2, style=QtCore.Qt.SolidLine)
    pen2 = pg.mkPen(color=clr_2, width=2, style=QtCore.Qt.DashLine)
    pen3 = pg.mkPen(color=clr_3, width=1, style=QtCore.Qt.SolidLine)
    pen4 = pg.mkPen(color=clr_4, width=2, style=QtCore.Qt.SolidLine)
    p1.getAxis('left').setTextPen(clr_1)
    p1.getAxis('right').setTextPen(clr_2)
    p1.getAxis('bottom').setTextPen('black')

    # avoids small glitch when re-zooming
    g.getPlotItem().enableAutoRange()

    # -----------------
    # graph DO loggers
    # -----------------
    if met == 'DO':
        # draw DO (y1) and T (y2) lines
        p1.setLabel("left", lbl1, **_sty(clr_1))
        p1.getAxis('right').setLabel(lbl2, **_sty(clr_2))
        p1.plot(x, y1, pen=pen1, hoverable=True)
        p2.addItem(pg.PlotCurveItem(x, y2, pen=pen2, hoverable=True))

        # dynamic upper top of DO
        upper_top_do = 10
        if max(y1) > upper_top_do:
            upper_top_do = max(y1) + 1
        upper_top_do = int(ceil(upper_top_do))

        # y-axis ranges, bottom-axis label
        p1.setYRange(0, upper_top_do, padding=0)
        p2.setYRange(min(y2), max(y2), padding=0)
        p1.getAxis('bottom').setLabel(title, **_sty('black'))

        # alpha, for zones, the lower, the more transparent
        alpha = 85
        if _zt == 'zones OFF':
            return
        g.addItem(FiniteLinearRegionItem(values=(0, 2),
                                         limits=4,
                                         orientation="horizontal",
                                         brush=(255, 0, 0, alpha),
                                         movable=False))
        g.addItem(FiniteLinearRegionItem(values=(2, 4),
                                         limits=4,
                                         orientation="horizontal",
                                         brush=(255, 170, 6, alpha),
                                         movable=False))
        g.addItem(FiniteLinearRegionItem(values=(4, 6),
                                         limits=4,
                                         orientation="horizontal",
                                         brush=(255, 255, 66, alpha),
                                         movable=False))
        g.addItem(FiniteLinearRegionItem(values=(6, upper_top_do),
                                         limits=4,
                                         orientation="horizontal",
                                         brush=(176, 255, 66, alpha),
                                         movable=False))

    # -----------------------------------------
    # graph old Temperature / Pressure loggers
    # -----------------------------------------
    if met == 'TP':
        # draw T and D lines
        p1.setLabel("left", lbl1, **_sty(clr_1))
        p1.getAxis('right').setLabel(lbl2, **_sty(clr_2))
        p1.plot(x, y1, pen=pen1, hoverable=True)
        p2.addItem(pg.PlotCurveItem(x, y2, pen=pen2, hoverable=True))

        # y-axis ranges, bottom-axis label
        p1.setYRange(0, max(y1) + _axis_room(y1), padding=0)
        p2.setYRange(min(y2), max(y2), padding=0)
        p1.getAxis('bottom').setLabel(title, **_sty('black'))

    # ------------------
    # graph TDO loggers
    # ------------------
    if met == 'TDO':
        a.cb_g_switch_tp.setVisible(True)
        tdo_graph_type = a.cb_g_switch_tp.currentText()

        # type of TDO plot 1/2: D (y1) & T (y2) vs time
        if 'x-time' in tdo_graph_type:
            p1.setLabel("left", lbl1, **_sty(clr_1))
            p1.getAxis('right').setLabel(lbl2, **_sty(clr_2))
            # set any pressure value < 0 to 0
            arr = np.array(y1)
            arr[arr < 0] = 0
            y1 = list(arr)
            p1.plot(x, y1, pen=pen1, hoverable=True)
            p2.addItem(pg.PlotCurveItem(x, y2, pen=pen2, hoverable=True))

            # left y inverted: 1st parameter y-up, 2nd y-low
            # .1 prevents displaying negative pressure values
            p1.setYRange(.01, max(y1), padding=0)
            # right y not inverted: 1st parameter y-low, 2nd y-up
            p2.setYRange(min(y2), max(y2), padding=0)

            # bottom-axis label
            p1.getAxis('bottom').setLabel(title, **_sty('black'))

            # ------------------------
            # 3rd line: accelerometer
            # ------------------------
            if not linux_is_rpi():
                # add 3rd axis
                p1.layout.addItem(ax3, 2, 3)
                ax3.setStyle(tickFont=font)
                ax3.setLabel(lbl3, **_sty(clr_3))
                ax3.setTextPen(pen3)

                # get indexes with interesting accelerometer data
                w = 2
                th = 3
                li = get_interesting_idx_ma(y5, w, th)

                # simulate arrows height
                # y5 = [140] * len(y5)

                # add some more accelerometer arrows
                n = int(len(y5) / 5)
                if n > 0:
                    yn = [i for i in range(0, len(y5), n)]
                    li += yn
                    # print('yn', yn)

                    # add arrows
                    for i in li:
                        a = pg.ArrowItem(
                            # 180 faces right
                            angle=180,
                            tipAngle=60,
                            headLen=20,
                            tailLen=20,
                            tailWidth=10,
                            pen=pen3,
                            brush=clr_3
                        )
                        a.setPos(x[i], y5[i])
                        p3.addItem(a)

                # add text
                # a = pg.TextItem('alarm', color='orange', border='green', angle=45)
                # a.setPos(x[10], y3[10])
                # a.setFont(QFont('Times', 20))
                # p3.addItem(a)

                # range
                p3.setYRange(0, max(y3), padding=0)

        # type of TDO plot 2/2: T (y2) / D (y1) vs time
        elif 'x-Temp' in tdo_graph_type:
            p1.getAxis('left').setTextPen(clr_4)
            p1.setLabel("left", 'Depth (fathoms)' + ' ─', **_sty(clr_4))

            # remove whole right axis
            g.getPlotItem().hideAxis('right')

            # set any pressure value < 0 to 0
            arr = np.array(y1)
            arr[arr < 0] = 0
            y1 = list(arr)

            # chop, this graph mess x-axis when outliers
            # ls_idx = _get_outliers_indexes(y2, 10, 90)
            # cy1 = [j for i, j in enumerate(y1) if i not in ls_idx]
            # cy2 = [j for i, j in enumerate(y2) if i not in ls_idx]
            # print(f'{len(cy1) / len(y1)}% of the points here')
            # in this case, x-ticks are T
            # p1.plot(x=cy2, y=cy1, pen=pen4, hoverable=True)

            # don't modify
            p1.plot(x=y2, y=y1, pen=pen4, hoverable=True)

            # left y inverted: 1st parameter y-up, 2nd y-low
            # .1 prevents displaying negative pressure values
            p1.setYRange(.1, max(y1), padding=0)

            # title and bottom axis
            title = f'Temperature (F) {title}'
            p1.getAxis('bottom').setLabel(title, **_sty('black'))

            # patch for bottom ticks, y2 are floats
            # solves the problem of the x-axis ticks changing
            bt = []
            _i = min(y2)
            while _i < max(y2):
                bt.append(_i)
                # _i += 1
                _i += ((max(y2) - min(y2)) / 10)
            p1.getAxis('bottom').setTicks(([[(v, '{:5.1f}'.format(v)) for v in bt]]))

            # or we could set the x-axis label on top
            # a.g.setTitle(e, color="red", size="15pt")

    # statistics: benchmark and number of points
    end_ts = time.perf_counter()
    el_ts = int((end_ts - start_ts) * 1000)
    lg.a(f'graphed {len(x)} {met} points, took {el_ts} ms')

    # statistics: average box in main tab
    _u(f"{STATE_DDS_BLE_DOWNLOAD_STATISTICS}/")
    is_rpi = linux_is_rpi()
    if met == 'TDO':
        if (not is_rpi) or (is_rpi and r == 'BLE'):
            dp = data['Pressure (dbar) TDO']
            dt = data['Temperature (F) TDO']
            # calculate 80th percentile threshold float
            # we only keep values at the bottom of sea
            p80 = _percentile(dp, 80)
            ls_p, ls_t = [], []
            for i, p in enumerate(dp):
                if p >= p80:
                    ls_p.append(dp[i])
                    ls_t.append(dt[i])
            lg.a(f'debug: percentile 80 is {p80}')
            s = 'haul mean\n'
            s += '{:5.2f} dbar\n'.format(mean(ls_p))
            s += '{:5.2f} °F'.format(mean(ls_t))
            _u(f"{STATE_DDS_BLE_DOWNLOAD_STATISTICS}/{s}")
    if met == 'DO':
        if (not is_rpi) or (is_rpi and r == 'BLE'):
            _do = data['DO Concentration (mg/l) DO']
            dt = data['Temperature (F) DO']
            s = 'haul mean\n'
            s += '{:5.2f} mg_l\n'.format(mean(_do))
            s += '{:5.2f} °F'.format(mean(dt))
            _u(f"{STATE_DDS_BLE_DOWNLOAD_STATISTICS}/{s}")


def process_n_graph(a, r=''):
    try:
        # ----------
        # graph it
        # ----------
        _graph_busy_sign_show(a)
        _process_n_graph(a, r)

        # remove any past error
        a.g.setTitle('')

    except GraphException as e:
        # errors such as "no data files to graph"
        a.g.setTitle(e, color="red", size="15pt")
        a.g.getAxis('bottom').setLabel("")

    except (Exception,) as ex:
        # not GraphException, but python errors such as IndexError
        e = 'undefined error, see log'
        a.g.setTitle(e, color="red", size="15pt")
        lg.a(f"error: graph_embed -> {str(ex)}")
        a.g.getAxis('bottom').setLabel("")

    finally:
        _graph_busy_sign_hide(a)
