import datetime
import os
import shlex
import socket
import time
import shutil
from math import ceil

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QDesktopWidget,
    QWidget,
    QMessageBox,
    QTableWidgetItem,
    QHeaderView, QTableWidget,
)
from ddh.db.db_his import DbHis
from ddh.draw_graph import graph_process_n_draw
from ddh.utils_maps import gui_populate_maps_tab
from dds.emolt import this_box_has_grouped_s3_uplink
from dds.timecache import is_it_time_to
from locales.locales import _x
from locales.strings import *
from mat.ble.ble_mat_utils import DDH_GUI_UDP_PORT
from mat.utils import linux_is_rpi
import subprocess as sp
import pyqtgraph as pg

from utils.ddh_config import (
    dds_get_cfg_vessel_name,
    dds_get_cfg_monitored_serial_numbers,
    dds_get_cfg_flag_graph_test_mode,
    dds_get_cfg_logger_sn_from_mac,
    dds_get_cfg_forget_time_secs,
    ddh_get_cfg_maps_en, dds_get_cfg_flag_download_test_mode, dds_get_cfg_box_sn, ddh_get_file_flag_plot_wc,
    dds_get_cfg_skip_dl_in_port_en)

from utils.ddh_shared import (
    STATE_DDS_BLE_SCAN,
    STATE_DDS_SOFTWARE_UPDATED,
    STATE_DDS_BLE_DOWNLOAD,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_HARDWARE_ERROR,
    STATE_DDS_BLE_DISABLED,
    STATE_DDS_BLE_APP_GPS_ERROR_POSITION,
    STATE_DDS_BLE_APP_GPS_ERROR_SPEED,
    STATE_DDS_NOTIFY_GPS_BOOT,
    STATE_DDS_BLE_DOWNLOAD_PROGRESS,
    STATE_DDS_BLE_SERVICE_INACTIVE,
    STATE_DDS_BLE_ANTENNA,
    STATE_DDS_NOTIFY_NET_VIA,
    STATE_DDS_NOTIFY_CLOUD_BUSY,
    STATE_DDS_NOTIFY_CLOUD_LOGIN,
    STATE_DDS_NOTIFY_CLOUD_OK,
    STATE_DDS_NOTIFY_CLOUD_ERR,
    STATE_DDS_NOTIFY_CONVERSION_ERR,
    STATE_DDS_NOTIFY_CONVERSION_OK,
    STATE_DDS_NOTIFY_BOAT_NAME,
    STATE_DDS_NOTIFY_GPS,
    STATE_DDS_GPS_POWER_CYCLE,
    STATE_DDS_NOTIFY_GPS_CLOCK,
    STATE_DDS_NOTIFY_GPS_NUM_SAT,
    STATE_DDS_NOTIFY_HISTORY,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS,
    ddh_get_folder_path_res,
    STATE_DDS_BLE_SCAN_FIRST_EVER,
    STATE_DDS_BLE_ERROR_MOANA_PLUGIN, STATE_DDS_BLE_DOWNLOAD_ERROR_GDO, STATE_DDS_BLE_ERROR_RUN,
    STATE_DDS_REQUEST_GRAPH,
    STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR,
    ddh_get_db_history_file,
    STATE_DDS_BLE_NO_ASSIGNED_LOGGERS,
    get_ddh_do_not_rerun_flag_li, ddh_get_root_folder_path, STATE_DDS_BLE_CONNECTING, STATE_DDS_PRESSED_BUTTON_2,
    get_ddh_local_sw_version, STATE_DDS_GPS_IN_PORT, STATE_DDS_BAD_CONF, STATE_DDS_BLE_DOWNLOAD_STATISTICS,
    STATE_DDS_PRESSED_BUTTON_1, send_ddh_udp_gui, STATE_DDS_BOOT_GUI,
)
from utils.logs import lg_gui as lg
from utils.wdog import gui_dog_touch

STR_NOTE_PURGE_BLACKLIST = "Purge all loggers' lock-out time?"
STR_NOTE_GPS_BAD = "Skipping logger until valid GPS fix is obtained"
_g_ts_gui_boot = time.perf_counter()
PERIOD_SHOW_LOGGER_DL_OK_SECS = 300
PERIOD_SHOW_LOGGER_DL_ERROR_SECS = 300
PERIOD_SHOW_BLE_APP_GPS_ERROR_POSITION = 60
g_lock_icon_timer = 0
g_app_uptime = time.perf_counter()
dim_done_day = 0
dim_done_night = 0
g_last_ci = ''
g_last_ct = ''


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


def _calc_app_uptime():
    return int(time.perf_counter() - g_app_uptime)


def _lock_icon(t):
    global g_lock_icon_timer
    g_lock_icon_timer = t


def gui_setup_timers(a):
    # timer to update GUI fields
    a.tg = QTimer()
    a.tg.timeout.connect(a._tg_fxn)
    a.tg.start(1000)

    # timer to measure RPi temperature
    a.tt = QTimer()
    a.tt.timeout.connect(a._tt_fxn)
    if linux_is_rpi():
        a.tt.start(1000)

    # timer BLE service alive
    a.tb = QTimer()
    a.tb.timeout.connect(a._tb_fxn)
    a.tb.start(30000)


def gui_setup_graph_tab(a):
    a.g = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
    a.lay_g_h2.addWidget(a.g)
    a.g.setBackground('w')
    a.btn_g_next_haul.setEnabled(False)
    a.btn_g_next_haul.setVisible(False)
    a.lbl_graph_busy.setVisible(False)
    a.cb_g_switch_tp.setVisible(False)
    gui_manage_graph_test_files()


def gui_create_variables(a):
    a.bright_idx = 2
    a.tab_edit_hide = True
    a.tab_advanced_hide = True
    a.tab_graph_hide = True
    a.tab_edit_wgt_ref = None
    a.tab_map_wgt_ref = None
    a.tab_note_wgt_ref = None
    a.tab_recipe_wgt_ref = None
    a.tab_graph_wgt_ref = None
    a.key_pressed = None
    a.num_clicks_brightness = 9  # index for 100%
    a.lbl_ble_img_filled = False
    a.boat_pressed = 0
    a.commit_pressed = 0
    a.datetime_pressed = 0
    a.lbl_net_pressed = 0
    a.lbl_uptime_pressed = 0
    a.gif_map = None
    a.n_good_maps = 0
    a.i_good_maps = 0
    a.map_filename = None


def gui_setup_view(my_win):
    """fills window with titles and default contents"""
    a = my_win
    a.setupUi(a)
    a.setWindowTitle("Lowell Instruments' Deck Data Hub")
    a.tabs.setTabIcon(0, QIcon("ddh/gui/res/icon_info.png"))
    a.tabs.setTabIcon(1, QIcon("ddh/gui/res/icon_setup.png"))
    a.tabs.setTabIcon(2, QIcon("ddh/gui/res/icon_exclamation.png"))
    a.tabs.setTabIcon(3, QIcon("ddh/gui/res/icon_history.ico"))
    a.tabs.setTabIcon(4, QIcon("ddh/gui/res/icon_tweak.png"))
    a.tabs.setTabIcon(5, QIcon("ddh/gui/res/icon_graph.ico"))
    a.tabs.setTabIcon(6, QIcon("ddh/gui/res/icon_waves.png"))
    a.setWindowIcon(QIcon("ddh/gui/res/icon_lowell.ico"))
    a.lbl_brightness.setPixmap(QPixmap("ddh/gui/res/bright.png"))
    a.lbl_boat.setPixmap(QPixmap("ddh/gui/res/img_boat.png"))
    a.lbl_net.setPixmap(QPixmap("ddh/gui/res/img_wireless_color.png"))
    a.lbl_cloud_img.setPixmap(QPixmap("ddh/gui/res/upcloud.png"))
    ship = dds_get_cfg_vessel_name()
    a.lbl_boat_txt.setText(ship)
    a.setCentralWidget(a.tabs)
    a.tabs.setCurrentIndex(0)

    # info: lat, lon, time
    a.lbl_gps.setText('-\n-')

    # info: box SN
    a.lbl_box_sn.setText('DDH ' + dds_get_cfg_box_sn())

    # cloud: aws, cell
    a.lbl_cloud_txt.setText("-")
    a.bar_dl.setVisible(False)

    # load default values for edit tab
    a.btn_load_current.animateClick()

    # load git commit display or version
    # dc = "version: {}".format(get_ddh_commit())
    dc = f"v. {get_ddh_local_sw_version()}"
    a.lbl_commit.setText(dc)

    # checkboxes rerun flag
    rerun_flag = not get_ddh_do_not_rerun_flag_li()
    a.chk_rerun.setChecked(rerun_flag)

    # maps enable flag
    me = ddh_get_cfg_maps_en()
    a.chk_b_maps.setChecked(me)

    # plot data outside the water
    plot_only_in_water = ddh_get_file_flag_plot_wc()
    a.chk_plt_only_inside_water.setChecked(plot_only_in_water)

    # test mode
    a.lbl_testmode.setVisible(False)
    if dds_get_cfg_flag_download_test_mode():
        a.lbl_testmode.setVisible(True)

    # dl statistics
    a.lbl_summary_dl.setVisible(False)

    # edit tab dropdowns
    a.cbox_gear_type.addItems(["fixed", "mobile"])
    a.cb_s3_uplink_type.addItems(["raw", "group"])
    a.cb_skip_in_port.addItems(["False", "True"])

    # allow to have more room
    a.cb_g_paint_zones.setVisible(False)

    if this_box_has_grouped_s3_uplink():
        a.cb_s3_uplink_type.setCurrentIndex(1)
    if dds_get_cfg_skip_dl_in_port_en():
        a.cb_skip_in_port.setCurrentIndex(1)

    return a


def gui_show_boot_icon(_):
    send_ddh_udp_gui(STATE_DDS_BOOT_GUI)


def gui_center_window(my_app):
    """on RPi, DDH app uses full screen"""
    a = my_app

    if linux_is_rpi():
        # rpi is 800 x 480
        a.showFullScreen()
        return

    qr = a.frameGeometry()
    cp = QDesktopWidget().availableGeometry().center()
    qr.moveCenter(cp)
    a.move(300, 200)
    a.setFixedWidth(1024)
    a.setFixedHeight(768)


def gui_manage_graph_test_files():
    a = str(ddh_get_root_folder_path())
    d0 = a + '/dl_files/00-00-00-00-00-00'
    d1 = a + '/dl_files/11-22-33-44-55-66'
    d2 = a + '/dl_files/99-99-99-99-99-99'
    d3 = a + '/dl_files/55-55-55-55-55-55'
    d4 = a + '/dl_files/33-33-33-33-33-33'
    t0 = a + '/tests/00-00-00-00-00-00'
    t1 = a + '/tests/11-22-33-44-55-66'
    t2 = a + '/tests/99-99-99-99-99-99'
    t3 = a + '/tests/55-55-55-55-55-55'
    t4 = a + '/tests/33-33-33-33-33-33'
    shutil.rmtree(d0, ignore_errors=True)
    shutil.rmtree(d1, ignore_errors=True)
    shutil.rmtree(d2, ignore_errors=True)
    shutil.rmtree(d3, ignore_errors=True)
    shutil.rmtree(d4, ignore_errors=True)
    if dds_get_cfg_flag_graph_test_mode():
        shutil.copytree(t0, d0)
        shutil.copytree(t1, d1)
        shutil.copytree(t2, d2)
        shutil.copytree(t3, d3)
        shutil.copytree(t4, d4)
        lg.a('copied logger graph test folders')


def gui_populate_history_tab(my_app):
    """
    fills history table on history tab
    """

    # clear the table
    a = my_app
    a.tbl_his.tableWidget = None
    a.tbl_his.tableWidget = QTableWidget()
    a.tbl_his.tableWidget.setRowCount(20)
    a.tbl_his.tableWidget.setColumnCount(3)
    a.tbl_his.tableWidget.setSortingEnabled(0)

    # get the history database and order by most recent first
    db = DbHis(ddh_get_db_history_file())
    r = db.get_all().values()
    r = sorted(r, key=lambda x: x["ep_loc"], reverse=True)

    # we will show just one entry per mac
    fil_r = []
    already = []
    for i, h in enumerate(r):
        if h['mac'] not in already:
            already.append(h['mac'])
            fil_r.append(h)

    # we only have one, the newest, history entry per mac
    for i, h in enumerate(fil_r):
        e = h["e"]
        e = "success" if e == "ok" else e
        try:
            a.tbl_his.setItem(i, 0, QTableWidgetItem(str(h["SN"])))
            lat = "{:+6.4f}".format(float(h["lat"]))
            lon = "{:+6.4f}".format(float(h["lon"]))
            dt = datetime.datetime.fromtimestamp(int(h["ep_loc"]))
            t = dt.strftime("%b %d %H:%M")
            a.tbl_his.setItem(i, 1, QTableWidgetItem(f"{e} {t} at {lat}, {lon}"))
            a.tbl_his.setItem(i, 2, QTableWidgetItem(str(h['rerun'])))

        except (Exception,) as ex:
            lg.a(f"error: history frame {h} -> {ex}")

    # redistribute columns with
    a.tbl_his.horizontalHeader().resizeSection(0, 120)
    a.tbl_his.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    # columns' title labels
    labels = ["logger", "result", "rerun"]
    a.tbl_his.setHorizontalHeaderLabels(labels)


def gui_ddh_populate_note_tab_dropdown(my_app):
    """fills dropdown list in note tab"""

    a = my_app
    a.lst_macs_note_tab.clear()

    j = dds_get_cfg_monitored_serial_numbers()
    for each in j:
        a.lst_macs_note_tab.addItem(each)


def gui_ddh_populate_graph_dropdown_sn(my_app):
    """fills logger serial number dropdown list in graph tab"""

    a = my_app
    a.cb_g_sn.clear()

    if dds_get_cfg_flag_graph_test_mode():
        a.cb_g_sn.addItem('SNtest000')
        a.cb_g_sn.addItem('SNtest111')
        a.cb_g_sn.addItem('SNtest999')
        a.cb_g_sn.addItem('SNtest555')
        a.cb_g_sn.addItem('SNtest333')
        return

    # from HISTORY database, grab serial numbers, most recent first
    db = DbHis(ddh_get_db_history_file())
    r = db.get_all().values()
    r = sorted(r, key=lambda x: x["ep_loc"], reverse=True)
    h_sn = []
    for h in r:
        if not h['SN']:
            continue
        if h['SN'] not in h_sn:
            h_sn.append(h['SN'].lower())

    # from CONFIGURATION file, grab serial numbers
    c_sn = dds_get_cfg_monitored_serial_numbers()
    c_sn = [i.lower() for i in c_sn]

    # add first HISTORY ones, next CONFIGURATION ones
    for i in h_sn:
        a.cb_g_sn.addItem(i)
    for i in c_sn:
        if i not in h_sn:
            a.cb_g_sn.addItem(i)


def gui_setup_buttons(my_app):
    """link buttons and labels clicks and signals"""
    a = my_app

    # hidden buttons
    if not linux_is_rpi():
        a.btn_sms.setEnabled(True)

    # clicks in BLE text, boat image, brightness...
    a.lbl_ble.mousePressEvent = a.click_lbl_ble
    a.lbl_cnv.mousePressEvent = a.click_lbl_cnv
    a.lbl_cloud_img.mousePressEvent = a.click_lbl_cloud_img
    a.lbl_brightness.mousePressEvent = a.click_lbl_brightness
    a.lbl_brightness_txt.mousePressEvent = a.click_lbl_brightness
    a.lbl_boat.mousePressEvent = a.click_lbl_boat_pressed
    a.lbl_boat.mouseReleaseEvent = a.click_lbl_boat_released
    a.lbl_commit.mousePressEvent = a.click_lbl_commit_pressed
    a.lbl_commit.mouseReleaseEvent = a.click_lbl_commit_released
    a.lbl_date.mousePressEvent = a.click_lbl_datetime_pressed
    a.lbl_date.mouseReleaseEvent = a.click_lbl_datetime_released
    a.lbl_net.mousePressEvent = a.click_lbl_net_pressed
    a.lbl_net.mouseReleaseEvent = a.click_lbl_net_released
    a.lbl_uptime.mousePressEvent = a.click_lbl_uptime_pressed
    a.lbl_uptime.mouseReleaseEvent = a.click_lbl_uptime_released
    a.lbl_map.mousePressEvent = a.click_lbl_map_pressed

    # buttons' connections
    a.btn_known_clear.clicked.connect(a.click_btn_clear_known_mac_list)
    a.btn_see_all.clicked.connect(a.click_btn_see_all_macs)
    # see current macs
    a.btn_see_cur.clicked.connect(a.click_btn_see_monitored_macs)
    a.btn_arrow.clicked.connect(a.click_btn_arrow_move_entries)
    # save configuration
    a.btn_setup_apply.clicked.connect(a.click_btn_edit_tab_save_config)
    a.btn_close_wo_save.clicked.connect(a.click_btn_edit_tab_close_wo_save)
    a.btn_dl_purge.clicked.connect(a.click_btn_purge_dl_folder)
    a.btn_his_purge.clicked.connect(a.click_btn_purge_his_db)
    a.btn_adv_purge_lo.clicked.connect(a.click_btn_adv_purge_lo)
    # load current settings
    a.btn_load_current.clicked.connect(a.click_btn_load_current_json_file)
    a.btn_note_yes.clicked.connect(a.click_btn_note_yes)
    a.btn_note_no.clicked.connect(a.click_btn_note_no)
    a.btn_note_yes_specific.clicked.connect(a.click_btn_note_yes_specific)
    a.chk_rerun.toggled.connect(a.click_chk_rerun)
    a.chk_b_maps.toggled.connect(a.click_chk_b_maps)
    a.chk_plt_only_inside_water.toggled.connect(a.click_chk_plt_only_inside_water)
    a.cb_s3_uplink_type.activated.connect(a.click_cb_s3_uplink_type)
    a.btn_sms.clicked.connect(a.click_btn_sms)
    a.btn_map_next.clicked.connect(a.click_btn_map_next)

    # graph stuff
    a.btn_g_reset.clicked.connect(a.click_graph_btn_reset)
    a.btn_g_next_haul.clicked.connect(a.click_graph_btn_next_haul)
    a.cb_g_sn.activated.connect(a.click_graph_listview_logger_sn)
    a.cb_g_cycle_haul.activated.connect(a.click_graph_lbl_haul_types)
    a.cb_g_paint_zones.activated.connect(a.click_graph_btn_paint_zones)
    a.cb_g_switch_tp.activated.connect(a.click_graph_cb_switch_tp)


def gui_hide_edit_tab(ui):
    # find tab ID, index and keep ref
    p = ui.tabs.findChild(QWidget, "tab_setup")
    i = ui.tabs.indexOf(p)
    ui.tab_edit_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def gui_show_edit_tab(ui):
    icon = QIcon("ddh/gui/res/icon_setup.png")
    ui.tabs.addTab(ui.tab_edit_wgt_ref, icon, " Setup")
    p = ui.tabs.findChild(QWidget, "tab_setup")
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def gui_hide_map_tab(ui):
    p = ui.tabs.findChild(QWidget, "tab_map")
    i = ui.tabs.indexOf(p)
    ui.tab_map_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def gui_hide_maps_next_btn(ui):
    ui.btn_map_next.setVisible(False)


def gui_hide_advanced_tab(ui):
    # find tab ID, index and keep ref
    p = ui.tabs.findChild(QWidget, "tab_advanced")
    i = ui.tabs.indexOf(p)
    ui.tab_recipe_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def gui_hide_graph_tab(ui):
    if not linux_is_rpi():
        return
    if os.path.exists('/home/pi/li/.ddh_graph_enabler.json'):
        return
    # find tab ID, index and keep ref
    p = ui.tabs.findChild(QWidget, "tab_graph")
    i = ui.tabs.indexOf(p)
    ui.tab_graph_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def gui_show_graph_tab(ui):
    icon = QIcon("ddh/gui/res/icon_graph.ico")
    ui.tabs.addTab(ui.tab_graph_wgt_ref, icon, " Graphs")
    p = ui.tabs.findChild(QWidget, "tab_graph")
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def gui_show_advanced_tab(ui):
    icon = QIcon("ddh/gui/res/icon_tweak.png")
    ui.tabs.addTab(ui.tab_recipe_wgt_ref, icon, " Advanced")
    p = ui.tabs.findChild(QWidget, "tab_advanced")
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def gui_show_map_tab(ui):
    icon = QIcon("ddh/gui/res/icon_waves.png")
    ui.tabs.addTab(ui.tab_map_wgt_ref, icon, " Maps")
    p = ui.tabs.findChild(QWidget, "tab_map")
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def gui_hide_note_tab(ui):
    p = ui.tabs.findChild(QWidget, "tab_note")
    i = ui.tabs.indexOf(p)
    ui.tab_note_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def gui_show_note_tab_delete_black_macs(ui):
    icon = QIcon("ddh/gui/res/icon_exclamation.png")
    ui.tabs.addTab(ui.tab_note_wgt_ref, icon, " Note")
    ui.lbl_note.setText(STR_NOTE_PURGE_BLACKLIST)
    p = ui.tabs.findChild(QWidget, "tab_note")
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def gui_dict_from_list_view(l_v):
    """grab listview entries 'name mac' and build a dict"""
    d = dict()
    n = l_v.count()
    for _ in range(n):
        it = l_v.item(_)
        pair = it.text().split()
        d[pair[0]] = pair[1]
    return d


def gui_add_to_history_database(mac, e, lat, lon, ep_loc, ep_utc, rerun, u):
    sn = dds_get_cfg_logger_sn_from_mac(mac)
    db = DbHis(ddh_get_db_history_file())
    db.add(mac, sn, e, lat, lon, ep_loc, ep_utc, rerun, u)


def gui_confirm_by_user(s):
    """ask user to press OK or CANCEL"""

    m = QMessageBox()
    m.setIcon(QMessageBox.Information)
    m.setWindowTitle("warning")
    m.setText(s)
    choices = QMessageBox.Ok | QMessageBox.Cancel
    m.setStandardButtons(choices)
    return m.exec_() == QMessageBox.Ok


def _parse_addr(my_app, addr):
    ip, _ = addr
    # if ip != "127.0.0.1":
    #     my_app.lbl_ip.setText("remote DDH")


def _gui_update_icon_timer():
    global g_lock_icon_timer
    if g_lock_icon_timer:
        g_lock_icon_timer -= 1


def _gui_did_icon_change(my_app, ci, ct, cf):

    if cf == STATE_DDS_BLE_SCAN and g_lock_icon_timer:
        # cases we don't update
        return False

    if ci:
        img = f"{str(ddh_get_folder_path_res())}/{ci}"
        my_app.lbl_ble_img.setPixmap(QPixmap(img))
    if ct:
        my_app.lbl_ble.setText(ct)
    return True


def _gui_parse_udp(my_app, s, ip="127.0.0.1"):

    a = my_app
    i = int(time.perf_counter()) % 4

    # when this > 0, the BLE_SCAN_ICON cannot appear
    global g_lock_icon_timer

    f, v = s.split("/")
    # lg.a('UDP | parsing \'{}/{}\''.format(f, v))

    global g_last_ci
    global g_last_ct

    # variables for big icon and text
    ci = ""
    ct = ""
    cf = f

    # -------------------
    # BLE service states
    # -------------------
    if f in (
            STATE_DDS_BLE_SCAN,
            STATE_DDS_BLE_SCAN_FIRST_EVER
    ):
        ct = _x(STR_SEARCHING_FOR_LOGGERS)
        ci = f"blue{i}.png"

    elif f == STATE_DDS_SOFTWARE_UPDATED:
        ct = _x(STR_DDH_UPDATED)
        ci = "update.png"

    elif f == STATE_DDS_BOOT_GUI:
        ct = _x(STR_DDH_BOOTING)
        ci = "booting.png"

    elif f == STATE_DDS_BLE_CONNECTING:
        ct = f'{_x(STR_CONNECTING_LOGGER)} {v}'
        ci = f'ble_connecting.png'

    elif f == STATE_DDS_BLE_DOWNLOAD:
        ct = f'{_x(STR_DOWNLOADING_LOGGER)} {v}'
        ci = "dl2.png"
        a.bar_dl.setValue(0)

    elif f == STATE_DDS_BLE_DOWNLOAD_OK:
        _lock_icon(PERIOD_SHOW_LOGGER_DL_OK_SECS)
        ct = f'{_x(STR_DOWNLOADING_LOGGER_DONE)} {v}'
        ci = "ok.png"
        g_last_ci = ci
        g_last_ct = ct

    elif f == STATE_DDS_BLE_RUN_STATUS:
        if v == "off":
            _lock_icon(PERIOD_SHOW_LOGGER_DL_OK_SECS)
            ct = _x(STR_STOPPED_AUTOWAKE_OFF)
            ci = "attention.png"
            g_last_ci = ci
            g_last_ct = ct

    elif f == STATE_DDS_BLE_DOWNLOAD_STATISTICS:
        # v: can be filled or empty, also it needs a small patch
        v = v.replace('mg_l', 'mg/l')
        a.lbl_summary_dl.setText(v)
        a.lbl_summary_dl.setVisible(bool(v))
        ci = g_last_ci
        ct = g_last_ct

    elif f == STATE_DDS_BLE_DOWNLOAD_WARNING:
        # at least same value as orange mac
        _lock_icon(15)
        ct = f'{v} {_x(STR_RETRYING_LOGGER)}'
        ci = "sand_clock.png"

    elif f == STATE_DDS_BLE_DOWNLOAD_ERROR:
        # when a logger totally fails
        _lock_icon(PERIOD_SHOW_LOGGER_DL_ERROR_SECS)
        ct = f'{v} {_x(STR_LOGGER_FAILURE)}'
        ci = "error.png"

    elif f == STATE_DDS_BLE_DOWNLOAD_ERROR_GDO:
        ct = _x(STR_LOGGER_ERROR_OX_SENSOR)
        ci = "error.png"

    elif f == STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR:
        ct = _x(STR_LOGGER_ERROR_TP_SENSOR)
        ci = "error.png"

    elif f == STATE_DDS_BLE_ERROR_RUN:
        ct = _x(STR_LOGGER_ERROR_RUN)
        ci = "error.png"

    elif f == STATE_DDS_BLE_HARDWARE_ERROR:
        # 0 because we might send it after a dl_OK, which displays long
        _lock_icon(0)
        ct = _x(STR_LOGGER_ERROR_RADIO)
        ci = "blue_err.png"

    elif f == STATE_DDS_PRESSED_BUTTON_1:
        a.keyPressEvent(ButtonPressEvent(Qt.Key_1))

    elif f == STATE_DDS_PRESSED_BUTTON_2:
        a.keyPressEvent(ButtonPressEvent(Qt.Key_2))

    elif f == STATE_DDS_BLE_DISABLED:
        _lock_icon(1)
        ct = _x(STR_RADIO_IS_DISABLED)
        ci = "blue_dis.png"

    elif f == STATE_DDS_BLE_APP_GPS_ERROR_POSITION:
        ct = _x(STR_NEED_GPS)
        ci = "gps_err.png"
        a.lbl_gps.setText("-\n-")
        a.lbl_gps_sat.setText("-")

    elif f == STATE_DDS_BLE_APP_GPS_ERROR_SPEED:
        ct = _x(STR_APP_RESTING)
        ci = f"blue{i}.png"

    elif f == STATE_DDS_NOTIFY_GPS_BOOT:
        # shows the progress of boot GPS boot
        v = int(v)
        ct = f'{_x(STR_WAITING_GPS_SECONDS)} {v}'
        ci = f"gps_boot{i}.png"

    elif f == STATE_DDS_BLE_DOWNLOAD_PROGRESS:
        v = int(float(v))
        if v == -1:
            a.bar_dl.setVisible(False)
        else:
            if not a.lbl_ble_img_filled:
                ct = f"{_x(STR_DOWNLOADING_LOGGER)}..."
                ci = "dl2.png"
            a.bar_dl.setVisible(True)
            a.bar_dl.setValue(v)

    elif f == STATE_DDS_BLE_SERVICE_INACTIVE:
        ct = _x(STR_NO_BLE_SERVICE)
        ci = "blue_err.png"
        a.lbl_antenna.setText("")

    elif f == STATE_DDS_BLE_ANTENNA:
        a.lbl_antenna.setText(v)

    elif f == STATE_DDS_BLE_ERROR_MOANA_PLUGIN:
        ct = "moana plugin needed"
        ci = "moana_plugin.png"

    elif f == STATE_DDS_BAD_CONF:
        ct = _x(STR_DDS_BAD_CONF)
        ci = "bad_conf.png"

    # -------------------
    # NET service states
    # -------------------
    elif f == STATE_DDS_NOTIFY_NET_VIA:
        a.lbl_net_txt.setText(v)
        if v in ("wifi", "wi-fi"):
            ssid = gui_get_my_current_wlan_ssid()
            a.lbl_net_txt.setText(ssid)

    # -------------------
    # CLOUD states
    # -------------------
    elif f == STATE_DDS_NOTIFY_CLOUD_BUSY:
        a.lbl_cloud_txt.setText("busy")
    elif f == STATE_DDS_NOTIFY_CLOUD_LOGIN:
        a.lbl_cloud_txt.setText("err_login")
    elif f == STATE_DDS_NOTIFY_CLOUD_OK:
        a.lbl_cloud_txt.setText("OK")
    elif f == STATE_DDS_NOTIFY_CLOUD_ERR:
        a.lbl_cloud_txt.setText("error")

    # -------------------
    # CONVERSION states
    # -------------------
    elif f == STATE_DDS_NOTIFY_CONVERSION_ERR:
        a.lbl_cnv.setText("cnv_error")
    elif f == STATE_DDS_NOTIFY_CONVERSION_OK:
        a.lbl_cnv.setText("cnv_ok")

    # -----------
    # GRAPH fields
    # -----------
    elif f == STATE_DDS_REQUEST_GRAPH:
        if ip != "127.0.0.1":
            lg.a("not graphing remote downloads")
            return
        graph_process_n_draw(a, r='BLE')

    # ----------------------------------
    # other fields that are not states
    # ----------------------------------
    elif f == STATE_DDS_NOTIFY_BOAT_NAME:
        a.lbl_boat_txt.setText(v)

    elif f == STATE_DDS_GPS_IN_PORT:
        _lock_icon(15)
        ct = _x(STR_WE_ARE_IN_PORT)
        ci = "gps_in_port.png"

    elif f == STATE_DDS_NOTIFY_GPS:
        a.lbl_gps.setText(v)

    elif f == STATE_DDS_GPS_POWER_CYCLE:
        # time controlled via function calling this state
        ct = _x(STR_WAIT_POWER_CYCLE_GPS)
        ci = "gps_power_cycle.png"

    elif f == STATE_DDS_NOTIFY_GPS_CLOCK:
        ct = _x(STR_SYNCING_GPS_TIME)
        ci = "gps_clock.png"

    elif f == STATE_DDS_NOTIFY_GPS_NUM_SAT:
        a.lbl_gps_sat.setText(f"{v} GPS satellites")

    elif f == STATE_DDS_NOTIFY_HISTORY:
        if v.startswith("add"):
            # history/add&{mac}&{ok|error}&{lat}&{lon}&{ep_loc}&{ep_utc}&{rerun}&{uuid}
            v = v.split("&")
            gui_add_to_history_database(v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8])
        gui_populate_history_tab(a)
        gui_ddh_populate_graph_dropdown_sn(a)

    elif f == STATE_DDS_BLE_LOW_BATTERY:
        ct = _x(STR_LOGGER_LOW_BATTERY)
        ci = "low_battery.png"

    elif f == STATE_DDS_BLE_NO_ASSIGNED_LOGGERS:
        ct = _x(STR_NO_LOGGERS_ASSIGNED)
        ci = "attention_old.png"

    else:
        lg.a(f"UDP | unknown state: {f}")

    # -----------------------------------------------------------------
    # update big icon
    #      - sleep() after sending a signal, blocks the icon
    #      - lock_icon() prevents BLE_SCAN from appearing for a while
    # -----------------------------------------------------------------
    _icon_updated = _gui_did_icon_change(a, ci, ct, cf)

    # stats box left visible or not
    if not ci:
        return

    # progress bar visible or not
    if f not in (
            STATE_DDS_BLE_DOWNLOAD,
            STATE_DDS_BLE_DOWNLOAD_PROGRESS
    ):
        a.bar_dl.setVisible(False)

    # stats box visible on green (dl_OK) orange (dl_OK not rerun) ticks
    if _icon_updated and ci not in ("ok.png", "attention.png"):
        my_app.lbl_summary_dl.setVisible(False)


# socket gui
_skg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_skg.settimeout(0.1)
_skg.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
_skg.bind(("127.0.0.1", DDH_GUI_UDP_PORT))


def gui_timer_fxn(my_app):
    a = my_app

    # useful to know if GUI crashed
    gui_dog_touch()

    # dim brightness depending on night / day
    # gui_dim_screen_depending_on_hour(a)

    # update the maps tab, prevent freeze at boot
    if ddh_get_cfg_maps_en() and\
            _calc_app_uptime() > 10 and\
            is_it_time_to('update_maps_tab', 3600):
        gui_populate_maps_tab(a)

    _gui_update_icon_timer()
    i = int(time.perf_counter()) % 4
    a.lbl_date.setText(datetime.datetime.now().strftime("%b %d %H:%M:%S"))

    if a.boat_pressed > 0:
        a.boat_pressed += 1
    if a.commit_pressed > 0:
        a.commit_pressed += 1
    if a.datetime_pressed > 0:
        a.datetime_pressed += 1
    if a.lbl_net_pressed > 0:
        a.lbl_net_pressed += 1
    if a.lbl_uptime_pressed > 0:
        a.lbl_uptime_pressed += 1

    _u = bytes()
    try:
        while 1:
            _u, addr = _skg.recvfrom(1024)
            _parse_addr(my_app, addr)
            # -------------------------------
            # attend to queue of GUI messages
            # -------------------------------
            _gui_parse_udp(my_app, _u.decode())
    except socket.timeout:
        pass

    # how long this GUI has been up, it restarts every GUI launch
    _up = datetime.timedelta(seconds=time.perf_counter() - _g_ts_gui_boot)
    a.lbl_uptime.setText("uptime " + str(_up).split(".")[0])

    # force normally show first tab
    _ti = a.tabs.currentIndex()
    _pf = int(time.perf_counter())
    if _ti != 0 and _pf % 1800 == 0:
        a.tabs.setCurrentIndex(0)

    # animate BLE icon
    if a.lbl_ble.text() == _x("searching for loggers"):
        ci = f"blue{i}.png"
        fol_res = str(ddh_get_folder_path_res())
        ci = f"{fol_res}/{ci}"
        a.lbl_ble_img.setPixmap(QPixmap(ci))


def gui_json_get_forget_time_secs():
    t = dds_get_cfg_forget_time_secs()
    assert t >= 600
    return t


def gui_ddh_set_brightness(a):
    if not linux_is_rpi():
        lg.a("not raspberry, not setting brightness control")
        return

    d = {
        0: 12.75, 18: 12.75,
        1: 25.5 * 2, 17: 25.5 * 2,
        2: 25.5 * 3, 16: 25.5 * 3,
        3: 25.5 * 4, 15: 25.5 * 4,
        4: 25.5 * 5, 14: 25.5 * 5,
        5: 25.5 * 6, 13: 25.5 * 6,
        6: 25.5 * 7, 12: 25.5 * 7,
        7: 25.5 * 8, 11: 25.5 * 8,
        8: 25.5 * 9, 10: 25.5 * 9,
        9: 25.5 * 10
    }

    v = int(d[a.num_clicks_brightness])
    lg.a(f"setting brightness to {v}")
    b1 = '/sys/class/backlight/rpi_backlight/brightness"'
    b2 = '/sys/class/backlight/10-0045/brightness"'
    # requires root or $ chmod 777 /sys/class.../backlight
    s1 = f'bash -c "echo {str(v)} > {b1}'
    s2 = f'bash -c "echo {str(v)} > {b2}'
    o = sp.DEVNULL
    sp.run(shlex.split(s1), stdout=o, stderr=o)
    sp.run(shlex.split(s2), stdout=o, stderr=o)
    a.lbl_brightness_txt.setText(str(ceil(100 * v / 255)) + "%")


def gui_dim_screen_depending_on_hour(a):
    global dim_done_day
    global dim_done_night
    h = int(datetime.datetime.now().strftime("%H"))
    if 7 < h < 19 and not dim_done_day:
        lg.a('display: setting higher brightness during day')
        dim_done_day = 1
        dim_done_night = 0
        # a bit ugly but meh
        a.num_clicks_brightness = 9
        gui_ddh_set_brightness(a)
    if 19 < h < 7 and not dim_done_night:
        lg.a('display: dimmed during night')
        dim_done_night = 1
        dim_done_day = 0
        a.num_clicks_brightness = 0
        gui_ddh_set_brightness(a)


def gui_get_my_current_wlan_ssid() -> str:
    """gets connected wi-fi network name, if any"""

    if linux_is_rpi():
        c = "/usr/sbin/iwgetid -r"
        s = sp.run(c, shell=True, stdout=sp.PIPE)
        return s.stdout.decode().rstrip("\n")

    # when developing
    c = "nmcli -t -f name connection show --active"
    rv = sp.run(c, shell=True, stdout=sp.PIPE)
    if rv.returncode == 0:
        # rv.stdout: b'Candy_Corn\nwg0\n'
        return rv.stdout.decode().split("\n")[0]

    # this may return a command not found error
    c = "iwgetid -r"
    rv = sp.run(c, shell=True, stdout=sp.PIPE)
    if rv.returncode == 0:
        wifi_name = rv.stdout.decode().rstrip("\n")
        wifi_name = wifi_name.replace('Auto ', '')
        return wifi_name

    return ""
