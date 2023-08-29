from os.path import basename
import pyqtgraph as pg
from pathlib import Path
import psutil
import glob
import os
import pathlib
import shutil
import sys
import matplotlib
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QMainWindow, QFileDialog
import ddh.gui.designer_main as d_m
from ddh.db.db_his import DBHis
from ddh.graph import graph_embed
from ddh.utils_graph import graph_get_fol_list
from ddh.utils_gui import (
    gui_json_get_metrics,
    gui_hide_edit_tab,
    gui_hide_note_tab,
    gui_populate_history,
    gui_plot_db_delete,
    gui_ddh_set_brightness,
    gui_setup_view,
    gui_setup_buttons,
    gui_center_window,
    gui_setup_buttons_rpi,
    gui_refresh_dl_folder_list,
    gui_yaml_load_pairs,
    gui_json_get_mac_n_name_pairs,
    dict_from_list_view,
    gui_show_edit_tab,
    gui_gen_ddh_json_content,
    gui_json_get_forget_time_secs,
    STR_NOTE_PURGE_BLACKLIST,
    gui_confirm_by_user,
    gui_show_note_tab_delete_black_macs,
    gui_timer_fxn,
    gui_ddh_populate_note_tab_dropdown,
    gui_json_set_plot_units,
    gui_hide_recipes_tab,
    gui_show_recipes_tab,
    gui_hide_graph_tab,
    gui_setup_graph_tab, gui_show_graph_tab,
)

from dds.emolt import this_box_has_grouped_s3_uplink, GROUPED_S3_FILE_FLAG
from liu.linux import linux_is_process_running
from mat.utils import linux_is_rpi
from settings import ctx
from utils.ddh_shared import (
    get_ddh_folder_path_dl_files,
    ddh_get_json_plot_type,
    ddh_get_settings_json_file,
    ddh_get_gui_closed_flag_file,
    dds_kill_by_pid_file,
    dds_get_json_vessel_name,
    ddh_get_db_history_file,
    get_ddh_folder_path_macs_black,
    NAME_EXE_DDS,
    send_ddh_udp_gui,
    ddh_get_disabled_ble_flag_file,
    dds_get_mac_from_sn_from_json_file,
    get_ddh_folder_path_settings,
    ddh_get_app_override_flag_file,
    STATE_DDS_REQUEST_PLOT,
    dds_get_aws_has_something_to_do_via_gui_flag_file,
    ble_get_cc26x2_recipe_flags_from_json,
    ble_set_cc26x2r_recipe_flags_to_file,
    STATE_DDS_BLE_SERVICE_INACTIVE,
    dds_get_ddh_got_an_update_flag_file,
    STATE_DDS_SOFTWARE_UPDATED,
    get_dl_files_type, dds_kill_by_pid_file_only_child,
)

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from utils.logs import lg_gui as lg  # noqa: E402
import subprocess as sp  # noqa: E402


class DDH(QMainWindow, d_m.Ui_MainWindow):
    def __init__(self):
        super(DDH, self).__init__()
        self.plt_cnv = MplCanvas(self, width=5, height=3, dpi=100)
        gui_setup_view(self)
        gui_setup_buttons(self)
        gui_center_window(self)
        gui_setup_buttons_rpi(self)

        # ------------------------
        # you want GUI logs or not
        # ------------------------
        lg.are_enabled(True)

        # for future new plotting
        self.aw = None

        # gui: appearance
        dl_fol = str(get_ddh_folder_path_dl_files())
        self.plt_fol_list = gui_refresh_dl_folder_list(dl_fol)
        self.plt_fol_idx = 0
        self.plt_fol = None
        self.plt_time_spans = ("h", "d", "w", "m", "y")
        self.plt_ts = self.plt_time_spans[0]
        self.plt_ts_idx = 0
        self.cb_plot_type.addItems(["fixed", "mobile"])
        self.cb_s3_uplink_type.addItems(["raw", "group"])
        self.plt_metrics = gui_json_get_metrics()
        self.gear_type = ddh_get_json_plot_type()
        self.bright_idx = 2
        self.tab_edit_hide = True
        self.tab_recipes_hide = True
        self.tab_edit_wgt_ref = None
        self.tab_note_wgt_ref = None
        self.tab_recipe_wgt_ref = None
        self.tab_graph_wgt_ref = None
        self.key_pressed = None
        self.num_clicks_brightness = 10
        self.lbl_ble_img_filled = False
        self.boat_pressed = 0
        self.commit_pressed = 0
        self.datetime_pressed = 0
        self.lbl_net_pressed = 0
        gui_json_set_plot_units()
        gui_hide_edit_tab(self)
        gui_hide_recipes_tab(self)
        gui_hide_note_tab(self)
        gui_populate_history(self)
        gui_plot_db_delete()
        gui_ddh_set_brightness(self)
        gui_ddh_populate_note_tab_dropdown(self)

        # s3 uplink type field
        if this_box_has_grouped_s3_uplink():
            self.cb_s3_uplink_type.setCurrentIndex(1)

        # graph tab
        gui_hide_graph_tab(self)
        self.g = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.g_fol_ls_idx = 0
        self.g_haul_text_options = [
            'all hauls',
            'last haul',
            'one haul'
        ]
        self.g_haul_text_options_idx = 0
        self.g_haul_idx = -1

        self.g_just_booted = True
        self.g_paint_zones = 'zones' # or 'zoom'
        gui_setup_graph_tab(self)

        # timer to update GUI fields
        self.tg = QTimer()
        self.tg.timeout.connect(self._tg_fxn)
        self.tg.start(1000)

        # timer to measure RPi temperature
        self.tt = QTimer()
        self.tt.timeout.connect(self._tt_fxn)
        if linux_is_rpi():
            self.tt.start(1000)

        # timer BLE service alive
        self.tb = QTimer()
        self.tb.timeout.connect(self._tb_fxn)
        self.tb.start(30000)

        # timer PLT message
        self.tp = QTimer()
        self.tp.timeout.connect(self._tp_fxn)

        # check if we had an update, also done at DDS
        file_flag = dds_get_ddh_got_an_update_flag_file()
        if os.path.exists(file_flag):
            send_ddh_udp_gui(STATE_DDS_SOFTWARE_UPDATED)

    def _tg_fxn(self):
        gui_timer_fxn(self)

    def _tt_fxn(self):
        # measure RAM usage of DDH box
        m = psutil.virtual_memory()
        if int(m.percent) > 75:
            ma = m.available / 1e9
            s = "debug: {:.2f}% GB of RAM used, {:.2f} GB available"
            lg.a(s.format(m.percent, ma))

        # measure temperature of DDH box, tell when too high
        self.tt.stop()
        c = "/usr/bin/vcgencmd measure_temp"
        rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)

        try:
            ans = rv.stdout
            if ans:
                # ans: b"temp=30.1'C"
                ans = ans.replace(b"\n", b"")
                ans = ans.replace(b"'C", b"")
                ans = ans.replace(b"temp=", b"")
                ans = float(ans.decode())
                if ans > 55:
                    lg.a("debug: {} degrees Celsius".format(ans))

        except (Exception,) as ex:
            lg.a("error: getting vcgencmd -> {}".format(ex))

        self.tt.start(600000)

    @staticmethod
    def _tb_fxn():
        name = NAME_EXE_DDS
        if not linux_is_process_running(name):
            lg.a("warning: BLE service seems dead")
            send_ddh_udp_gui(STATE_DDS_BLE_SERVICE_INACTIVE)

    def _tp_fxn(self):
        self.tp.stop()
        self.lbl_plt_msg.setVisible(False)

    def click_btn_clear_known_mac_list(self):
        self.lst_mac_org.clear()
        self.lst_mac_dst.clear()

    def click_btn_clear_see_all_macs(self):
        """loads (mac, name) pairs from yaml file"""

        self.lst_mac_org.clear()
        fol = str(get_ddh_folder_path_settings())
        f = QFileDialog.getOpenFileName(
            QFileDialog(), "Choose file", fol, "YAML files (*.yml)"
        )
        pairs = gui_yaml_load_pairs(f)
        if not pairs:
            return
        for m, n in pairs.items():
            s = "{}  {}".format(m, n)
            self.lst_mac_org.addItem(s)

    def click_btn_see_macs_in_current_json_file(self):
        """loads (mac, name) pairs in ddh.json file"""

        self.lst_mac_org.clear()
        pairs = gui_json_get_mac_n_name_pairs()
        for m, n in pairs.items():
            s = "{}  {}".format(m, n)
            self.lst_mac_org.addItem(s)

    def click_btn_arrow_move_entries(self):
        """move items in upper box to lower box"""

        ls = self.lst_mac_org.selectedItems()
        o = dict()
        for i in ls:
            pair = i.text().split()
            o[pair[0]] = pair[1]

        # dict from all items in lower box
        b = self.lst_mac_dst
        d_b = dict_from_list_view(b)
        d_b.update(o)

        # update lower box
        self.lst_mac_dst.clear()
        for m, n in d_b.items():
            s = "{}  {}".format(m, n)
            self.lst_mac_dst.addItem(s)

    def click_btn_apply_write_json_file(self):
        """creates a user ddh.json file"""

        l_v = self.lst_mac_dst
        pairs = dict_from_list_view(l_v)

        # input: <mac, name> pairs and forget_time
        try:
            t = int(self.lne_forget.text())
        except ValueError:
            t = 0
        self.lne_forget.setText(str(t))

        # input: vessel name
        ves = self.lne_vessel.text()

        # last haul
        lhf = self.cb_plot_type.currentIndex()

        if t < 600:
            self.lbl_setup_result.setText("bad forget_time")
            return
        if not ves:
            self.lbl_setup_result.setText("bad vessel name")
            return

        # we seem good to go
        s = "restarting DDH..."
        self.lbl_setup_result.setText(s)
        j = gui_gen_ddh_json_content(pairs, ves, t, lhf)
        with open(str(ddh_get_settings_json_file()), "w") as f:
            f.write(j)

        # bye, bye DDS
        dds_kill_by_pid_file_only_child()

        # bye, bye DDH
        lg.a("quit by save config button")
        sys.stderr.close()
        os._exit(0)

    def click_lbl_ble(self, _):
        # sequence: press key, depress, click
        k = self.key_pressed
        self.key_pressed = None
        # lg.a('key pressed is {}'.format(k))

        if k == "m":
            self.showMinimized()

        elif k == "b":
            ctx.ble_en = not ctx.ble_en
            s = "enabled" if ctx.ble_en else "disabled"
            lg.a("BLE {} by keypress".format(s))
            flag = ddh_get_disabled_ble_flag_file()
            if ctx.ble_en:
                pathlib.Path(flag).touch()
            else:
                if os.path.isfile(flag):
                    os.unlink(flag)

        elif k == "e":
            teh = self.tab_edit_hide = not self.tab_edit_hide
            gui_hide_edit_tab(self) if teh else gui_show_edit_tab(self)

        elif k == "q":
            p = ddh_get_gui_closed_flag_file()
            pathlib.Path.touch(p, exist_ok=True)
            dds_kill_by_pid_file()
            lg.a("closing by keypress 'q'")
            sys.stderr.close()
            os._exit(0)

    @staticmethod
    def click_lbl_uptime(_):
        p = ddh_get_gui_closed_flag_file()
        pathlib.Path.touch(p, exist_ok=True)
        dds_kill_by_pid_file()
        lg.a("closing by lbl_uptime clicked")
        sys.stderr.close()
        os._exit(0)

    def click_lbl_brightness(self, _):
        # no shift key, adjust DDH brightness
        v = (self.num_clicks_brightness + 1) % 11
        self.num_clicks_brightness = 1 if v == 0 else v
        gui_ddh_set_brightness(self)

    def click_btn_purge_dl_folder(self):
        """deletes contents in 'download files' folder"""

        d = str(get_ddh_folder_path_dl_files())
        lg.a("pressed btn_purge_dl_folder")
        s = "sure to delete dl_files folder?"
        if not gui_confirm_by_user(s):
            return

        try:
            if "dl_files" not in str(d):
                return
            shutil.rmtree(str(d), ignore_errors=True)
            self.plt_fol_list = gui_refresh_dl_folder_list(d)
            self.plt_fol_idx = 0
            self.plt_fol = None
        except OSError as e:
            lg.a("error {} : {}".format(d, e))

    def click_btn_purge_his_db(self):
        """deletes contents in history database"""

        s = "sure to purge history?"
        if gui_confirm_by_user(s):
            path_db = ddh_get_db_history_file()
            db = DBHis(path_db)
            db.delete_all_records()
        gui_populate_history(self)

    def click_btn_load_current_json_file(self):
        """updates EDIT tab from current 'ddh.json' file"""

        ves = dds_get_json_vessel_name()
        f_t = gui_json_get_forget_time_secs()
        lhf = ddh_get_json_plot_type()
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))
        # set index of the dropdown list
        self.cb_plot_type.setCurrentIndex(lhf)

    def click_btn_note_yes_specific(self):
        s = self.lbl_note.text()

        # only affects purge_macs note, not BLE GPS one
        if s == STR_NOTE_PURGE_BLACKLIST:
            try:
                p = get_ddh_folder_path_macs_black()
                n = self.lst_macs_note_tab.count()

                for i in range(n):
                    if not self.lst_macs_note_tab.item(i).isSelected():
                        continue

                    sn = self.lst_macs_note_tab.item(i).text()
                    mac = dds_get_mac_from_sn_from_json_file(sn)
                    mac = mac.replace(":", "-")
                    mask = "{}/{}@*".format(p, mac)
                    ff = glob.glob(mask)
                    for f in ff:
                        os.unlink(f)
                        s = "warning: clear lock-out selective for {}"
                        lg.a(s.format(f))

            except (OSError, Exception) as ex:
                lg.a("error: {}".format(ex))
                return

        lg.a("pressed note button 'OK'")
        flag = ddh_get_app_override_flag_file()
        pathlib.Path(flag).touch()
        lg.a("BLE op conditions override set as 1")
        gui_hide_note_tab(self)
        self.tabs.setCurrentIndex(0)

    def click_btn_note_yes(self):
        s = self.lbl_note.text()

        # only affects purge_macs note, not BLE GPS one
        if s == STR_NOTE_PURGE_BLACKLIST:
            try:
                p = get_ddh_folder_path_macs_black()
                mask = "{}/*".format(p)
                ff = glob.glob(mask)
                for f in ff:
                    os.unlink(f)
                    s = "warning: clear lock-out all for {}"
                    lg.a(s.format(f))

            except (OSError, Exception) as ex:
                lg.a("error: {}".format(ex))
                return

        lg.a("pressed note button specific 'OK'")
        flag = ddh_get_app_override_flag_file()
        pathlib.Path(flag).touch()
        lg.a("BLE op conditions override set as 1")
        gui_hide_note_tab(self)
        self.tabs.setCurrentIndex(0)

    def click_btn_note_no(self):
        gui_hide_note_tab(self)
        self.tabs.setCurrentIndex(0)
        lg.a("pressed note button 'CANCEL'")

    def closeEvent(self, ev):
        ev.accept()
        p = ddh_get_gui_closed_flag_file()
        pathlib.Path.touch(p, exist_ok=True)
        dds_kill_by_pid_file()
        lg.a("closing by clicking upper-right X")
        sys.stderr.close()
        os._exit(0)

    def keyPressEvent(self, ev):
        self.key_pressed = None
        known_keys = (
            Qt.Key_1,
            Qt.Key_2,
            Qt.Key_3,
            Qt.Key_B,
            Qt.Key_M,
            Qt.Key_W,
            Qt.Key_E,
            Qt.Key_Q,
            Qt.Key_I,
        )
        if ev.key() not in known_keys:
            lg.a("warning: unknown keypress {}".format(ev.key()))
            return

        # update the folder list
        d = str(get_ddh_folder_path_dl_files())
        self.plt_fol_list = gui_refresh_dl_folder_list(d)

        # prevent div by zero
        plot_keys = (Qt.Key_1, Qt.Key_3)
        if ev.key() in plot_keys and not self.plt_fol_list:
            lg.a("warning: empty local list of plot folders")
            self.lbl_plt_msg.setText("no folders to plot")
            return

        # -----------------------
        # identify key pressed
        # -----------------------
        if ev.key() == Qt.Key_1:
            # button to change logger being plotted
            lg.a("debug: main_gui detect pressed button 1")
            self.plt_fol_idx += 1
            self.plt_fol_idx %= len(self.plt_fol_list)
            self.plt_fol = self.plt_fol_list[self.plt_fol_idx]

        elif ev.key() == Qt.Key_2:
            lg.a("debug: main_gui detect pressed button 2")
            # button to request deletion of all black macs
            gui_show_note_tab_delete_black_macs(self)
            return

        elif ev.key() == Qt.Key_3:
            lg.a("debug: main_gui detect pressed button 3")
            # button to change plot span
            if not self.plt_fol:
                lg.a("warning: no plot to set span for")
                return

            self.plt_ts_idx += 1
            self.plt_ts_idx %= len(self.plt_time_spans)
            self.plt_ts = self.plt_time_spans[self.plt_ts_idx]

        elif ev.key() == Qt.Key_M:
            self.key_pressed = "m"

        elif ev.key() == Qt.Key_B:
            self.key_pressed = "b"

        elif ev.key() == Qt.Key_E:
            self.key_pressed = "e"

        elif ev.key() == Qt.Key_Q:
            self.key_pressed = "q"

        elif ev.key() == Qt.Key_I:
            self.key_pressed = "i"

        elif ev.key() == Qt.Key_W:
            self.key_pressed = "w"

        # button press -> plot
        if ev.key() in plot_keys:
            ctx.g_p_d = self.plt_fol
            ctx.g_p_ax = self.plt_cnv.axes
            ctx.g_p_ts = self.plt_ts
            ctx.g_p_met = self.plt_metrics
            send_ddh_udp_gui(STATE_DDS_REQUEST_PLOT)

    def click_lbl_boat_pressed(self, _):
        self.boat_pressed = 1

    def click_lbl_boat_released(self, _):
        if self.boat_pressed >= 2:
            teh = self.tab_edit_hide = not self.tab_edit_hide
            gui_hide_edit_tab(self) if teh else gui_show_edit_tab(self)
        self.boat_pressed = 0

    def click_lbl_commit_pressed(self, _):
        self.commit_pressed = 1

    def click_lbl_commit_released(self, _):
        if self.commit_pressed >= 2:
            trh = self.tab_recipes_hide = not self.tab_recipes_hide
            gui_hide_recipes_tab(self) if trh else gui_show_recipes_tab(self)
        self.commit_pressed = 0

    def click_lbl_datetime_pressed(self, _):
        self.datetime_pressed = 1

    def click_lbl_datetime_released(self, _):
        if self.datetime_pressed >= 2:
            self.showMinimized()
        self.datetime_pressed = 0

    def click_lbl_net_pressed(self, _):
        # ------------------------
        # lbl_net is the NET icon
        # lbl_net_txt is the text
        # -------------------------
        self.lbl_net_pressed = 1

    def click_lbl_net_released(self, _):
        if self.lbl_net_pressed >= 2:
            gui_show_graph_tab(self)
        self.lbl_net_pressed = 0

    def click_cb_s3_uplink_type(self, _):
        s = self.cb_s3_uplink_type.currentText()
        if s == 'raw':
            os.unlink(GROUPED_S3_FILE_FLAG)
        if s == 'group':
            Path(GROUPED_S3_FILE_FLAG).touch(exist_ok=True)

    def click_lbl_cloud_img(self, _):
        self.lbl_cloud_txt.setText("checking")
        flag = dds_get_aws_has_something_to_do_via_gui_flag_file()
        pathlib.Path(flag).touch()
        lg.a("clicked cloud icon")

    def click_chk_rerun(self, _):
        v = self.chk_rerun.isChecked()
        j = ble_get_cc26x2_recipe_flags_from_json()
        j["rerun"] = int(v)
        ble_set_cc26x2r_recipe_flags_to_file(j)

    def click_btn_g_reset(self):
        self.g.getPlotItem().enableAutoRange()
        graph_embed(self)

    def click_btn_g_next_logger(self):
        # check folder list
        fol_ls = graph_get_fol_list()
        n = len(fol_ls)
        if n == 0:
            e = 'error: folder list empty'
            self.g.setTitle(e, color="red", size="15pt")
            return

        # reset haul index
        self.g_haul_idx = -1

        # change logger folder and draw graph
        self.g_fol_ls_idx = (self.g_fol_ls_idx + 1) % n
        fol_ls = graph_get_fol_list()
        fol = fol_ls[self.g_fol_ls_idx]
        lg.a('button graph switch to folder {}'.format(basename(fol)))
        self.click_btn_g_reset()
        graph_embed(self)

    def click_btn_g_next_haul(self):
        # check
        fol_ls = graph_get_fol_list()
        n = len(fol_ls)
        if n == 0:
            e = 'error: folder list empty'
            self.g.setTitle(e, color="red", size="15pt")
            return
        # keep logger, increase haul index and draw graph
        fol = fol_ls[self.g_fol_ls_idx]
        ft = get_dl_files_type(fol)
        if not ft:
            e = 'error: no hauls for this logger'
            self.g.setTitle(e, color="red", size="15pt")
            return
        how_many_hauls = len(glob.glob('{}/*{}'.format(fol, ft)))
        self.g_haul_idx = (self.g_haul_idx + 1) % how_many_hauls

        # remember this button is only active on haul_text == 'one haul'
        how_many_hauls = len(glob.glob('{}/*{}'.format(fol, ft)))
        self.g_haul_idx = (self.g_haul_idx + 1) % how_many_hauls
        lg.a('button graph switch haul index to {}'.format(self.g_haul_idx))
        graph_embed(self)

    def click_lbl_g_cycle_haul(self, _):
        # calculate next haul type in cycle
        self.g_haul_text_options_idx = (self.g_haul_text_options_idx + 1) % 3
        _ht = self.g_haul_text_options[self.g_haul_text_options_idx]
        self.lbl_g_cycle_haul.setText(_ht)

        # keep logger, change haul type among 3 and draw graph
        self.btn_g_next_haul.setEnabled(False)
        if 'one' in _ht:
            self.btn_g_next_haul.setEnabled(True)
        if not self.g_just_booted:
            graph_embed(self)
        self.g_just_booted = False

    def click_lbl_g_paint_zones(self, _):
        if self.g_paint_zones == 'zones':
            self.g_paint_zones = 'zoom'
        else:
            self.g_paint_zones = 'zones'
        self.lbl_g_paint_zones.setText(self.g_paint_zones)
        graph_embed(self)


def on_ctrl_c(signal_num, _):
    p = ddh_get_gui_closed_flag_file()
    pathlib.Path.touch(p, exist_ok=True)
    dds_kill_by_pid_file()
    lg.a("closing by ctrl + c")
    os._exit(signal_num)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
