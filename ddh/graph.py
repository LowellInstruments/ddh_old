import os
import time
from datetime import datetime
from glob import glob
import json
from PyQt5 import QtCore
from PyQt5.QtCore import QTime, QCoreApplication
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from os.path import basename
from pyqtgraph import LinearRegionItem
from ddh.utils_graph import utils_graph_read_fol_req_file, \
    utils_graph_get_abs_fol_list, process_graph_csv_data, \
    utils_graph_does_exist_fol_req_file, \
    utils_graph_delete_fol_req_file
from mat.utils import linux_is_rpi
from utils.ddh_shared import dds_get_json_mac_dns, \
    dds_get_mac_from_sn_from_json_file, \
    get_dl_folder_path_from_mac, \
    ddh_get_absolute_application_path, \
    get_number_of_hauls, dds_get_json_vessel_name, \
    ddh_get_settings_json_file
from utils.logs import lg_gra as lg


# to be able to zoom in RPi
pg.setConfigOption('leftButtonPan', False)


# plot objects
p1 = None
p2 = None
p3 = None
just_booted = True


class GraphException(Exception):
    pass


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
        return 'green'
    return 'green'


def _graph_get_json_units():
    j = str(ddh_get_settings_json_file())
    with open(j) as f:
        cfg = json.load(f)
    return cfg["units_temp"], cfg["units_depth"]


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

    # time this graphing thing
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

    # this will have the absolute path to folder to plot
    fol: str

    # show who asked for a graph
    if r == 'BLE':
        if not utils_graph_does_exist_fol_req_file():
            raise GraphException('error: no BLE requested folder to graph')
        fol = utils_graph_read_fol_req_file()
        lg.a('selected last BLE download {}'.format(fol))
        utils_graph_delete_fol_req_file()
    else:
        # people pressing graph buttons
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

    # ---------------
    # let's CLEAR it
    # ---------------
    global p1
    global p2
    global p3
    if p1:
        p1.clear()
    if p2:
        p2.clear()
    if p3:
        p3.clear()
    p1 = g.plotItem

    # grid or not
    g.showGrid(x=True, y=False)

    # line: create the 2nd
    p2 = pg.ViewBox(enableMenu=True)
    p1.showAxis('right')
    p1.scene().addItem(p2)
    p1.getAxis('right').linkToView(p2)
    p2.setXLink(p1)

    # line: create the 3rd, not show it yet
    p3 = pg.ViewBox()
    ax3 = pg.AxisItem('right')
    p1.scene().addItem(p3)
    ax3.linkToView(p3)
    p3.setXLink(p1)
    ax3.setZValue(-10000)

    # connect the thing when resizing
    _graph_update_views()
    p1.vb.sigResized.connect(_graph_update_views)

    # font: size of axis ticks text
    font = QtGui.QFont()
    font.setPixelSize(16)
    font.setBold(True)
    p1.getAxis("bottom").setStyle(tickFont=font)
    p1.getAxis("left").setStyle(tickFont=font)
    p1.getAxis("right").setStyle(tickFont=font)

    # --------------------------
    # PROCESS folder's CSV data
    # --------------------------
    filenames_hash = _graph_calc_hash_filenames(fol)
    data = process_graph_csv_data(fol, filenames_hash, _ht, a.g_haul_idx)
    if not data:
        raise GraphException(f'error: no data in folder {fol}')
    if 'ISO 8601 Time' not in data.keys():
        raise GraphException(f'error: no time data for {fol}')

    # x: time
    x = data['ISO 8601 Time']
    met = data['metric']

    # ----------
    # the title
    # ----------
    fmt = '%b %d %H:%M'
    # choose utcfromtimestamp() / fromtimestamp()
    t1 = datetime.fromtimestamp(x[0]).strftime(fmt)
    t2 = datetime.fromtimestamp(x[-1]).strftime(fmt)
    mac = basename(fol).replace('-', ':')
    sn = dds_get_json_mac_dns(mac)
    title = 'SN{} - {} to {}'.format(sn, t1, t2)
    if data['pruned']:
        title += ' (data trimmed)'
    # g.setTitle(title, color="black", size="15pt", bold=True)

    # default variables to show for each metric
    lbl1, lbl2, lbl3 = '', '', ''
    y1, y2, y3 = [], [], []
    if met == 'TP':
        lbl1 = 'Depth (fathoms) TP'
        lbl2 = 'Temperature (F) TP'
    elif met == 'DO':
        lbl1 = 'DO Concentration (mg/l) DO'
        lbl2 = 'Temperature (F) DO'
    elif met == 'TAP':
        lbl1 = 'Depth (fathoms) TAP'
        lbl2 = 'Temperature (F) TAP'
        lbl3 = 'Ax TAP'
        y3 = data['Ax TAP']
        y4 = data['Ay TAP']
        y5 = data['Az TAP']
    y1 = data[lbl1]
    y2 = data[lbl2]

    # see if we need to invert or de-invert
    p1.invertY('Depth' in lbl1)

    # axes styles, sides
    lbl1 = lbl1.replace(' TP', '').replace(' DO', '').replace(' TAP', '')
    lbl2 = lbl2.replace(' TP', '').replace(' DO', '').replace(' TAP', '')
    lbl3 = lbl3.replace(' TP', '').replace(' DO', '').replace(' TAP', '')
    clr_1 = _get_color_by_label(lbl1)
    clr_2 = _get_color_by_label(lbl2)
    clr_3 = _get_color_by_label(lbl3)
    lbl1 = lbl1 + ' ─'
    lbl2 = lbl2 + ' - -'
    lbl3 = lbl3 + ' ─'
    p1.setLabel("left", lbl1, **_sty(clr_1))
    p1.getAxis('right').setLabel(lbl2, **_sty(clr_2))
    p1.getAxis('left').setTextPen(clr_1)
    p1.getAxis('right').setTextPen(clr_2)

    # axes style, BOTTOM
    cb = 'black'
    # p1.getAxis('bottom').setLabel('Time', **_sty(cb))
    p1.getAxis('bottom').setLabel(title, **_sty(cb))
    p1.getAxis('bottom').setTextPen(cb)

    # ---------------------
    # DRAW the LINES
    # ---------------------
    pen1 = pg.mkPen(color=clr_1, width=2, style=QtCore.Qt.SolidLine)
    pen2 = pg.mkPen(color=clr_2, width=2, style=QtCore.Qt.DashLine)
    p1.plot(x, y1, pen=pen1, hoverable=True)
    p2.addItem(pg.PlotCurveItem(x, y2, pen=pen2, hoverable=True))

    # avoids small glitch when re-zooming
    g.getPlotItem().enableAutoRange()

    # axis ranges
    p1.setYRange(min(y1), max(y1), padding=0)
    p2.setYRange(min(y2), max(y2), padding=0)

    # custom adjustments
    if met == 'DO':
        p1.setYRange(0, 10, padding=0)
        # alpha: the lower, the more transparent
        alpha = 85
        if _zt == 'zones OFF':
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
        reg_do_l.setMovable(False)
        reg_do_m.setMovable(False)
        reg_do_h.setMovable(False)
        reg_do_g.setMovable(False)
        g.addItem(reg_do_l)
        g.addItem(reg_do_m)
        g.addItem(reg_do_h)
        g.addItem(reg_do_g)

    if met == 'TP':
        if 'Depth (f)' in lbl1:
            p1.setYRange(max(y1), 0, padding=0)

    if met == 'TAP':
        if 'Depth (f)' in lbl1:
            p1.setYRange(max(y1), 0, padding=0)

        # 3rd line: color axis title, ticks text, line, show it
        if not linux_is_rpi():
            p1.layout.addItem(ax3, 2, 3)
            ax3.setStyle(tickFont=font)
            pen3 = pg.mkPen(color=clr_3, width=2, style=QtCore.Qt.SolidLine)
            ax3.setLabel(lbl3, **_sty(clr_3))
            ax3.setTextPen(clr_3)
            p3.addItem(pg.PlotCurveItem(x, y3, pen=pen3, hoverable=True))
            p3.setYRange(min(y3), max(y3), padding=0)

    # statistics: display number of points
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
        ) or os.path.exists('/home/pi/li/.ddh_graph_enabler.json'):
            # ----------
            # graph it
            # ----------
            _graph_busy_sign_show(a)
            _process_n_graph(a, r)
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
    finally:
        _graph_busy_sign_hide(a)
