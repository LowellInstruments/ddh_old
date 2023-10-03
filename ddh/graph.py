import glob
import time
from datetime import datetime
from PyQt5.QtCore import QTime
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from os.path import basename
from pyqtgraph import LinearRegionItem
from ddh.utils_graph import graph_get_abs_fol_req_file, graph_get_fol_list, graph_get_data_csv, graph_check_fol_req_file, \
    graph_delete_fol_req_file
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


def has_this_mac_any_dl_files(mac, fol_ls):
    for i in fol_ls:
        if mac.lower() in i.lower():
            return True
    return False


def graph_update_views():
    # used when resizing
    global p1, p2
    p2.setGeometry(p1.vb.sceneBoundingRect())
    p2.linkedViewChanged(p1.vb, p2.XAxis)


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


def _graph_embed(a, r=''):

    # passed app, get graph
    g = a.g

    # time this thing
    start_ts = time.perf_counter()

    # fol_ls: list of absolute local 'dl_files/<mac>' folders
    fol_ls = graph_get_fol_list()

    # get current haul type
    _ht = a.cb_g_cycle_haul.currentText()

    # zones type
    _zt = a.cb_g_paint_zones.currentText()

    # haul idx
    if a.g_haul_idx is None:
        a.g_haul_idx = -1

    # get folder to graph
    fol: str
    sn = a.cb_g_sn.currentText()
    if sn:
        if sn.startswith('SN'):
            sn = sn[2:]
        mac = dds_get_mac_from_sn_from_json_file(sn).replace(':', '-')
        if not has_this_mac_any_dl_files(mac, fol_ls):
            raise GraphException(f'error: no files for sn {sn} mac {mac}')
        lg.a('selected dropdown sn {} mac {}'.format(sn, mac))
        fol = get_dl_folder_path_from_mac(mac)
        # fol: 'dl_files/<mac>, is not absolute, make it so
        fol = str(ddh_get_absolute_application_path()) + '/' + str(fol)
    else:
        if not graph_check_fol_req_file():
            raise GraphException('error: no BLE requested folder to graph')
        fol = graph_get_abs_fol_req_file()
        lg.a('selected last BLE download {}'.format(fol))
        graph_delete_fol_req_file()

    # -----------------
    # number of hauls
    # -----------------
    nh = get_number_of_hauls(fol)

    if r == 'ble':
        # in fact, do nothing
        pass

    if r == 'logger_listview':
        # in fact, do nothing
        pass

    if r == 'hauls_next':
        # remember this button is only active on haul_text == 'single'
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

    if r == 'zones_toggle':
        # in fact, do nothing
        print(_zt)

    # clear it
    global p1
    global p2
    if p1:
        p1.clear()
    if p2:
        p2.clear()
    p1 = g.plotItem

    # draw grid or not
    g.showGrid(x=True, y=False)

    # create the 2nd line
    p2 = pg.ViewBox(enableMenu=True)
    p1.showAxis('right')
    p1.scene().addItem(p2)
    p1.getAxis('right').linkToView(p2)
    p2.setXLink(p1)
    graph_update_views()
    p1.vb.sigResized.connect(graph_update_views)

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

    # -------------------------------------------
    # grab the folder's CSV data, filter by haul
    # -------------------------------------------
    data = graph_get_data_csv(fol, _ht, a.g_haul_idx)
    if 'ISO 8601 Time' not in data.keys():
        e = 'error: no time data'
        g.setTitle(e, color="red", size="15pt")
        return

    # x is the time and is already in seconds
    x = data['ISO 8601 Time']
    met = data['metric']

    # last 2 keys in order are the metrics
    lbl1 = list(data.keys())[2]
    lbl2 = list(data.keys())[3]
    y1 = data[lbl1]
    y2 = data[lbl2]

    # set the title
    fmt = '%b %d %H:%M'
    t1 = datetime.utcfromtimestamp(x[0]).strftime(fmt)
    t2 = datetime.utcfromtimestamp(x[-1]).strftime(fmt)
    mac = basename(fol).replace('-', ':')
    sn = dds_get_json_mac_dns(mac)
    title = 'SN{} - {} to {}'.format(sn, t1, t2)
    g.setTitle(title, color="black", size="15pt")

    # set the axes
    p1.setLabel("left", lbl1,
                **{"color": "red", "font-size": "20px"})
    p1.getAxis('left').setTextPen('red')
    p1.getAxis('right').setLabel(lbl2,
                                 **{"color": "blue", "font-size": "20px"})
    p1.getAxis('right').setTextPen('b')

    # draw it
    p1.plot(x, y1, pen='r')
    p2.addItem(pg.PlotCurveItem(x, y2, pen='b', hoverable=True))

    # avoid small glitch when re-zooming
    g.getPlotItem().enableAutoRange()

    # common ranges
    p1.setYRange(min(y1), max(y1), padding=0)
    p2.setYRange(min(y2), max(y2), padding=0)

    # custom adjustments
    if met == 'DO':
        p1.setYRange(0, 10, padding=0)
        alpha = 50
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


def graph_embed(a, r=''):
    # wrapper so exception-safe
    try:
        # debug: while we develop this
        v = dds_get_json_vessel_name()
        if v.lower() in (
            'joaquim',
            'greenfeet',
            'redfeet',
            'cubefarm',
            'archer22'
        ):
            _graph_embed(a, r)
        else:
            lg.a('warning: this DDH does no new graphs yet :)')
    except GraphException as e:
        a.g.setTitle(e, color="red", size="15pt")
    except (Exception,) as ex:
        # specific errors managed inside
        lg.a("error: graph_embed -> {}".format(ex))