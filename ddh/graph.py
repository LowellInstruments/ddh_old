import time
from datetime import datetime
from glob import glob

from PyQt5 import QtCore
from PyQt5.QtCore import QTime, QCoreApplication
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from os.path import basename
from pyqtgraph import LinearRegionItem
from ddh.utils_graph import utils_graph_read_fol_req_file, utils_graph_get_abs_fol_list, process_graph_csv_data, utils_graph_does_exist_fol_req_file, \
    utils_graph_delete_fol_req_file
from utils.ddh_shared import dds_get_json_mac_dns, dds_get_mac_from_sn_from_json_file, get_dl_folder_path_from_mac, \
    ddh_get_absolute_application_path, get_number_of_hauls, dds_get_json_vessel_name
from utils.logs import lg_gra as lg


# to be able to zoom in RPi
pg.setConfigOption('leftButtonPan', False)


# plot objects
p1 = None
p2 = None
just_booted = True


class GraphException(Exception):
    pass


class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        # PySide's QTime() initialiser fails miserably and dismisses args/kwargs
        return [QTime().addMSecs(value).toString('mm:ss') for value in values]


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
    global p1, p2
    p2.setGeometry(p1.vb.sceneBoundingRect())
    p2.linkedViewChanged(p1.vb, p2.XAxis)


def _graph_busy_sign_show(a):
    a.lbl_graph_busy.setVisible(True)
    QCoreApplication.processEvents()


def _graph_busy_sign_hide(a):
    a.lbl_graph_busy.setVisible(False)


def _graph_calc_hash_filenames(fol):
    _g_ff_t = sorted(glob("{}/{}".format(fol, "*_Temperature.csv")))
    _g_ff_p = sorted(glob("{}/{}".format(fol, "*_Pressure.csv")))
    _g_ff_do = sorted(glob("{}/{}".format(fol, "*_DissolvedOxygen.csv")))
    _g_ff_tap = sorted(glob("{}/{}".format(fol, "*_TAP.csv")))

    # so we can use cache
    return '\n'.join(_g_ff_t) + '\n'.join(_g_ff_p) +\
        '\n'.join(_g_ff_do) + '\n'.join(_g_ff_tap)


def _process_n_graph(a, r=''):

    # passed app, get graph
    g = a.g

    # time this thing
    start_ts = time.perf_counter()

    # fol_ls: list of absolute local 'dl_files/<mac>' folders
    fol_ls = utils_graph_get_abs_fol_list()

    # get current haul type
    _ht = a.cb_g_cycle_haul.currentText()

    # zones type
    _zt = a.cb_g_paint_zones.currentText()

    # haul idx
    if a.g_haul_idx is None:
        a.g_haul_idx = -1

    # this will contain the absolute path to folder to plot
    fol: str

    # decide who asked for a graph
    if r == 'BLE':
        if not utils_graph_does_exist_fol_req_file():
            raise GraphException('error: no BLE requested folder to graph')
        fol = utils_graph_read_fol_req_file()
        lg.a('selected last BLE download {}'.format(fol))
        utils_graph_delete_fol_req_file()
    else:
        sn = a.cb_g_sn.currentText()
        if not sn:
            raise GraphException('seems no one asked for a graph?')
        if sn.startswith('SN'):
            sn = sn[2:]
        mac = dds_get_mac_from_sn_from_json_file(sn).replace(':', '-')
        if not _graph_check_mac_has_dl_files(mac, fol_ls):
            raise GraphException(f'error: no files for sn {sn} mac {mac}')
        lg.a('selected dropdown sn {} / mac {}'.format(sn, mac))
        fol = get_dl_folder_path_from_mac(mac)
        # fol: 'dl_files/<mac>, is not absolute, make it so
        fol = str(ddh_get_absolute_application_path()) + '/' + str(fol)

    # number of hauls
    nh = get_number_of_hauls(fol)
    if r == 'hauls_next':
        # remember this button only active on haul_text == 'single'
        if nh == 0:
            raise GraphException(f'error: no hauls for {fol}')
        a.g_haul_idx = (a.g_haul_idx + 1) % nh
        lg.a(f'button haul index = {a.g_haul_idx}')
    if r == 'hauls_labels':
        if _ht == 'single':
            a.btn_g_next_haul.setEnabled(True)
            a.btn_g_next_haul.setVisible(True)
        else:
            a.btn_g_next_haul.setEnabled(False)
            a.btn_g_next_haul.setVisible(False)

    # ---------------
    # let's clear it
    # ---------------
    global p1
    global p2
    if p1:
        p1.clear()
    if p2:
        p2.clear()
    p1 = g.plotItem

    # grid or not
    g.showGrid(x=True, y=False)

    # create the 2nd line
    p2 = pg.ViewBox(enableMenu=True)
    p1.showAxis('right')
    p1.scene().addItem(p2)
    p1.getAxis('right').linkToView(p2)
    p2.setXLink(p1)
    _graph_update_views()
    p1.vb.sigResized.connect(_graph_update_views)

    # invert y on the right
    # p2.invertY(True)

    # tick color and text color of both left and right
    p1.getAxis('left').setTickPen('red')
    p1.getAxis('right').setTickPen('blue')
    p1.getAxis('bottom').setTickPen('black')
    p1.getAxis('bottom').setTextPen('black')

    # size of axis ticks text
    font = QtGui.QFont()
    font.setPixelSize(15)
    p1.getAxis("bottom").setStyle(tickFont=font)
    p1.getAxis("left").setStyle(tickFont=font)
    p1.getAxis("right").setStyle(tickFont=font)

    # -----------------------
    # grab folder's CSV data
    # -----------------------
    filenames_hash = _graph_calc_hash_filenames(fol)
    data = process_graph_csv_data(fol, filenames_hash, _ht, a.g_haul_idx)
    if not data:
        raise GraphException(f'error: no data for {fol}')
    if 'ISO 8601 Time' not in data.keys():
        raise GraphException(f'error: no time data for {fol}')

    # x: time
    x = data['ISO 8601 Time']
    met = data['metric']

    # data: {metric, time, DOC, DOT...}
    if met == 'TP':
        lbl1 = 'Temperature (C) MAT'
        lbl2 = 'Pressure (dbar) MAT'
        y1 = data[lbl1]
        y2 = data[lbl2]
    elif met == 'DO':
        lbl1 = 'DO Concentration (mg/l) DO'
        lbl2 = 'Temperature (C) DO'
        y1 = data[lbl1]
        y2 = data[lbl2]
    elif met == 'TAP':
        lbl1 = 'Temperature (C) TAP'
        lbl2 = 'Pressure (dbar) TAP'
        y1 = data[lbl1]
        y2 = data[lbl2]
        y3 = data['Ax TAP']
        y4 = data['Ay TAP']
        y5 = data['Az TAP']

    # ugly but meh
    lbl1 = lbl1.replace(' MAT', '').replace(' DO', '').replace(' TAP', '')
    lbl2 = lbl2.replace(' MAT', '').replace(' DO', '').replace(' TAP', '')

    # title
    fmt = '%b %d %H:%M'
    t1 = datetime.utcfromtimestamp(x[0]).strftime(fmt)
    t2 = datetime.utcfromtimestamp(x[-1]).strftime(fmt)
    mac = basename(fol).replace('-', ':')
    sn = dds_get_json_mac_dns(mac)
    title = 'SN{} - {} to {}'.format(sn, t1, t2)
    g.setTitle(title, color="black", size="15pt")

    # axes labels
    lbl1 = lbl1 + ' ─'
    lbl2 = lbl2 + ' - -'
    p1.setLabel("left", lbl1, **{"color": "b", "font-size": "20px"})
    p1.getAxis('left').setTextPen('b')
    p1.getAxis('right').setLabel(lbl2, **{"color": "red", "font-size": "20px"})
    p1.getAxis('right').setTextPen('r')

    # --------------
    # let's draw it
    # --------------
    pen1 = pg.mkPen(color='b', width=2, style=QtCore.Qt.SolidLine)
    pen2 = pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine)
    p1.plot(x, y1, pen=pen1)
    p2.addItem(pg.PlotCurveItem(x, y2, pen=pen2, hoverable=True))

    # avoids small glitch when re-zooming
    g.getPlotItem().enableAutoRange()

    # common ranges
    p1.setYRange(min(y1), max(y1), padding=0)
    p2.setYRange(min(y2), max(y2), padding=0)

    # custom adjustments
    if met == 'DO':
        p1.setYRange(0, 10, padding=0)
        # alpha: the lower, the more transparent
        alpha = 85
        if _zt != 'zones':
            return
        reg_do_l = FiniteLinearRegionItem(values=(0, 2),
                                           limits=4,
                                           orientation="horizontal",
                                           brush=(255, 0, 0, alpha))
        reg_do_m = FiniteLinearRegionItem(values=(2, 4),
                                       limits=4,
                                       orientation="horizontal",
                                       brush=(255, 170, 6, alpha))
        reg_do_h = FiniteLinearRegionItem(values=(4, 6),
                                       limits=4,
                                       orientation="horizontal",
                                       brush=(255, 255, 66, alpha))
        reg_do_g = FiniteLinearRegionItem(values=(6, 10),
                                       limits=4,
                                       orientation="horizontal",
                                       brush=(176, 255, 66, alpha))
        g.addItem(reg_do_l)
        g.addItem(reg_do_m)
        g.addItem(reg_do_h)
        g.addItem(reg_do_g)

    # display number of points
    end_ts = time.perf_counter()
    el_ts = int((end_ts - start_ts) * 1000)
    lg.a(f'displaying {len(x)} {met} points, took {el_ts} ms')


def process_n_graph(a, r=''):
    try:
        v = dds_get_json_vessel_name()
        # todo ---> remove this restriction for new graphing :)
        if v.lower() in (
            # lowell instruments machine names
            'joaquim',
            'greenfeet',
            'redfeet',
            'cubefarm',
            'archer22',
            'hx_10',
            'hx_11',
            'george_test'
        ):
            _graph_busy_sign_show(a)
            _process_n_graph(a, r)
            _graph_busy_sign_hide(a)
        else:
            lg.a('warning: this DDH does no new graphs yet :)')

    except GraphException as e:
        # errors such as "did not find any file to graph"
        a.g.setTitle(e, color="red", size="15pt")

    except (Exception,) as ex:
        # python errors such as IndexError
        e = 'undefined error, see log'
        a.g.setTitle(e, color="red", size="15pt")
        lg.a("error: graph_embed -> {}".format(ex))
