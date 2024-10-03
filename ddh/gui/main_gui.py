import datetime

import time

from pathlib import Path
import psutil
import glob
import os
import pathlib
import shutil
import sys
from PyQt5.QtCore import QTimer, Qt, QCoreApplication
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QMainWindow, QMessageBox
import ddh.gui.designer_main as d_m
from ddh.db.db_his import DbHis
from ddh.draw_graph import process_n_graph
from ddh.utils_gui import (
    gui_hide_edit_tab,
    gui_hide_note_tab,
    gui_populate_history_tab,
    gui_ddh_set_brightness,
    gui_setup_view,
    gui_setup_buttons,
    gui_center_window,
    gui_dict_from_list_view,
    gui_show_edit_tab,
    gui_json_get_forget_time_secs,
    STR_NOTE_PURGE_BLACKLIST,
    gui_confirm_by_user,
    gui_show_note_tab_delete_black_macs,
    gui_timer_fxn,
    gui_ddh_populate_note_tab_dropdown,
    gui_hide_advanced_tab,
    gui_show_advanced_tab,
    gui_hide_graph_tab,
    gui_show_graph_tab,
    gui_ddh_populate_graph_dropdown_sn,
    gui_hide_map_tab,
    gui_hide_maps_next_btn,
    gui_create_variables,
    gui_setup_graph_tab,
    gui_setup_timers
)
from dds.notifications_v2 import notify_via_sms
from dds.timecache import is_it_time_to
from mat.linux import linux_is_process_running
from utils.ddh_config import (
    dds_get_cfg_vessel_name,
    dds_get_cfg_logger_mac_from_sn,
    ddh_get_cfg_gear_type,
    cfg_load_from_file,
    dds_get_cfg_flag_ble_en,
    cfg_save_to_file,
    dds_get_cfg_monitored_pairs,
    ddh_get_cfg_maps_en)
from utils.ddh_shared import (
    get_ddh_folder_path_dl_files,
    ddh_get_gui_closed_flag_file,
    dds_kill_by_pid_file,
    get_ddh_folder_path_macs_black,
    NAME_EXE_DDS,
    send_ddh_udp_gui,
    ddh_get_disabled_ble_flag_file,
    ddh_get_app_override_flag_file,
    dds_get_aws_has_something_to_do_via_gui_flag_file,
    STATE_DDS_BLE_SERVICE_INACTIVE,
    dds_get_ddh_got_an_update_flag_file,
    STATE_DDS_SOFTWARE_UPDATED,
    ddh_get_db_history_file,
    ddh_kill_by_pid_file,
    get_ddh_toml_all_macs_content,
    set_ddh_do_not_rerun_flag_li,
    clr_ddh_do_not_rerun_flag_li,
    dds_get_cnv_requested_via_gui_flag_file,
    NAME_EXE_API,
    ddh_get_folder_path_res
)

from utils.logs import lg_gui as lg  # noqa: E402
import subprocess as sp  # noqa: E402

from utils.flag_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_PLOT_ONLY_DATA_IN_WATER
)
from utils.wdog import gui_dog_clear

_g_flag_ble_en = dds_get_cfg_flag_ble_en()


class DDH(QMainWindow, d_m.Ui_MainWindow):
    def __init__(self):

        super(DDH, self).__init__()
        gui_setup_view(self)
        gui_setup_buttons(self)
        gui_center_window(self)
        lg.are_enabled(True)
        gui_create_variables(self)
        gui_dog_clear()
        gui_ddh_set_brightness(self)

        # show and hide stuff
        gui_hide_edit_tab(self)
        gui_hide_advanced_tab(self)
        gui_hide_note_tab(self)
        gui_populate_history_tab(self)
        gui_hide_maps_next_btn(self)
        if not ddh_get_cfg_maps_en():
            gui_hide_map_tab(self)

        # fill stuff
        gui_ddh_populate_note_tab_dropdown(self)
        gui_ddh_populate_graph_dropdown_sn(self)
        gui_setup_graph_tab(self)
        gui_setup_timers(self)

        # check if we had an update, also done at DDS
        file_flag = dds_get_ddh_got_an_update_flag_file()
        if os.path.exists(file_flag):
            send_ddh_udp_gui(STATE_DDS_SOFTWARE_UPDATED)

        lg.a("OK: DDH GUI finished booting")

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
                if ans > 65:
                    lg.a(f"debug: box temperature {ans} degrees Celsius")

        except (Exception,) as ex:
            lg.a("error: getting vcgencmd -> {}".format(ex))

        # 600 seconds = 10 minutes
        self.tt.start(600000)

    @staticmethod
    def _tb_fxn():
        if not linux_is_process_running(NAME_EXE_DDS):
            if is_it_time_to('tell_BLE_dead', 1800):
                lg.a("warning: BLE service seems dead")
            send_ddh_udp_gui(STATE_DDS_BLE_SERVICE_INACTIVE)

    def click_btn_clear_known_mac_list(self):
        self.lst_mac_org.clear()
        self.lst_mac_dst.clear()

    def click_btn_see_all_macs(self):
        """loads (mac, name) pairs from all macs config section"""

        self.lst_mac_org.clear()
        pp = get_ddh_toml_all_macs_content()
        for m, n in pp.items():
            s = f"{m}  {n}"
            self.lst_mac_org.addItem(s)

    def click_btn_see_monitored_macs(self):
        """loads (mac, name) pairs from config file"""

        self.lst_mac_org.clear()
        pp = dds_get_cfg_monitored_pairs()
        for m, n in pp.items():
            s = f"{m}  {n}"
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
        d_b = gui_dict_from_list_view(b)
        d_b.update(o)

        # update lower box
        self.lst_mac_dst.clear()
        for m, n in d_b.items():
            if '-' in m:
                s = f'MAC {m} is wrong'
                gui_confirm_by_user(s)
                continue
            s = f"{m}  {n}"
            self.lst_mac_dst.addItem(s)

    def click_btn_edit_tab_close_wo_save(self):
        lg.a('edit tab: pressed the close without save button')
        self.tab_edit_hide = not self.tab_edit_hide
        gui_hide_edit_tab(self)
        self.tabs.setCurrentIndex(0)

    def click_btn_edit_tab_save_config(self):
        """creates a config file"""

        l_v = self.lst_mac_dst
        if not l_v:
            r = QMessageBox.question(self, 'Question',
                                     "Do you want to save an empty logger list?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r == QMessageBox.No:
                return
            lg.a('warning: saved a config without macs after confirmation')
        pairs = gui_dict_from_list_view(l_v)
        # pairs: {'11:22:33:44:55:66': '1234567'}

        # input: forget_time
        try:
            t = int(self.lne_forget.text())
        except ValueError:
            t = 0
        self.lne_forget.setText(str(t))

        # input: vessel name
        ves = self.lne_vessel.text()

        # last haul graph type
        lhf = self.cbox_gear_type.currentIndex()

        # skip in port
        sk = self.cb_skip_in_port.currentIndex()

        # maps, in hidden advanced tab
        me = self.chk_b_maps.isChecked()

        if t < 600:
            self.lbl_setup_result.setText("bad forget_time")
            return
        if not ves:
            self.lbl_setup_result.setText("bad vessel name")
            return

        save_cfg = cfg_load_from_file()
        save_cfg['behavior']["forget_time"] = t
        save_cfg['behavior']['ship_name'] = ves
        save_cfg['behavior']['gear_type'] = lhf
        save_cfg['monitored_macs'] = pairs
        save_cfg['flags']['skip_dl_in_port_en'] = sk
        save_cfg['flags']['maps_en'] = me
        cfg_save_to_file(save_cfg)

        # we seem good to go
        s = "restarting DDH..."
        self.lbl_setup_result.setText(s)
        lg.a("closing by save config button")

        # show the previous thing
        QCoreApplication.processEvents()
        time.sleep(1)

        # also kill the DDH API so crontab restarts it
        lg.a("kill API by save config button")
        c = f'killall {NAME_EXE_API}'
        sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)

        # bye, bye DDS
        dds_kill_by_pid_file(only_child=False)
        ddh_kill_by_pid_file(only_child=False)

        # bye, bye DDH
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
            global _g_flag_ble_en
            _g_flag_ble_en ^= 1
            s = "enabled" if _g_flag_ble_en else "disabled"
            lg.a("BLE {} by keypress".format(s))
            flag = ddh_get_disabled_ble_flag_file()
            if _g_flag_ble_en:
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

    def click_lbl_brightness(self, _):
        # no shift key, adjust DDH brightness
        # 5,20,30,40,50,60,70,80,90,100,90,80,70,60,50,40,30,20
        self.num_clicks_brightness = (self.num_clicks_brightness + 1) % 18
        gui_ddh_set_brightness(self)

    @staticmethod
    def click_btn_purge_dl_folder():
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
        except OSError as e:
            lg.a("error {} : {}".format(d, e))

    def click_btn_adv_purge_lo(self):
        gui_show_note_tab_delete_black_macs(self)

    def click_btn_sms(self):
        s: str
        if is_it_time_to('sms', 3600):
            s = 'sending'
            notify_via_sms('sms')
        else:
            s = 'already sent'
        self.btn_sms.setText(s)
        QCoreApplication.processEvents()
        time.sleep(2)
        self.btn_sms.setText("tech support")

    def click_btn_purge_his_db(self):
        """deletes contents in history database"""

        s = "sure to purge history?"
        if gui_confirm_by_user(s):
            db = DbHis(ddh_get_db_history_file())
            db.delete_all()
        gui_populate_history_tab(self)

    def click_btn_load_current_json_file(self):
        """updates EDIT tab from current config file"""

        ves = dds_get_cfg_vessel_name()
        f_t = gui_json_get_forget_time_secs()
        lhf = ddh_get_cfg_gear_type()
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))
        # set index of the JSON dropdown list
        self.cbox_gear_type.setCurrentIndex(lhf)

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
                    mac = dds_get_cfg_logger_mac_from_sn(sn)
                    if mac:
                        mac = mac.replace(":", "-")
                        mask = "{}/{}@*".format(p, mac)
                        ff = glob.glob(mask)
                        for f in ff:
                            os.unlink(f)
                            s = "debug: clear lock-out selective for {}"
                            lg.a(s.format(f))
                    else:
                        lg.a("warning: could not clear lock-out selective")

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
                mask = f"{p}/*"
                ff = glob.glob(mask)
                for f in ff:
                    os.unlink(f)
                    bn = os.path.basename(f)
                    lg.a(f"warning: clicked purge lock-out for {bn}")

            except (OSError, Exception) as ex:
                lg.a(f"error click_btn_note_yes -> {ex}")
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

        # ------------------------------
        # identify keyboard key pressed
        # ------------------------------
        if ev.key() == Qt.Key_1:
            lg.a("debug: main_gui detect pressed button 1")
            self.num_clicks_brightness = (self.num_clicks_brightness + 1) % 18
            gui_ddh_set_brightness(self)
            return

        elif ev.key() == Qt.Key_2:
            lg.a("debug: main_gui detect pressed button 2")
            gui_show_note_tab_delete_black_macs(self)
            return

        elif ev.key() == Qt.Key_3:
            lg.a("debug: main_gui detect pressed button 3")

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
            trh = self.tab_advanced_hide = not self.tab_advanced_hide
            gui_hide_advanced_tab(self) if trh else gui_show_advanced_tab(self)
        self.commit_pressed = 0

    def click_lbl_uptime_pressed(self, _):
        self.lbl_uptime_pressed = 1

    def click_lbl_uptime_released(self, _):
        if self.lbl_uptime_pressed >= 2:
            p = ddh_get_gui_closed_flag_file()
            pathlib.Path.touch(p, exist_ok=True)
            dds_kill_by_pid_file()
            lg.a("closing by lbl_uptime clicked")
            sys.stderr.close()
            os._exit(0)
        self.lbl_uptime_pressed = 0

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

    def click_lbl_map_pressed(self, ev):
        h = self.lbl_map.height()
        w = self.lbl_map.width()
        p = self.map_filename
        x = ev.pos().x()
        y = ev.pos().y()
        # x starts left, y starts top
        print('click', h, w, p, x, y)
        if p and '_dtm' in p:
            if (.3 * w <= x <= .6 * w and
                    .3 * h <= y <= .6 * h):
                print('click dtm central area')

    def click_lbl_net_released(self, _):
        if self.lbl_net_pressed >= 2:
            tgh = self.tab_graph_hide = not self.tab_graph_hide
            gui_hide_graph_tab(self) if tgh else gui_show_graph_tab(self)
        self.lbl_net_pressed = 0

    def click_cb_s3_uplink_type(self, _):
        s = self.cb_s3_uplink_type.currentText()
        p = LI_PATH_GROUPED_S3_FILE_FLAG
        if s == 'raw':
            os.unlink(p)
        if s == 'group':
            Path(p).touch(exist_ok=True)

    def click_lbl_cloud_img(self, _):
        self.lbl_cloud_txt.setText("checking")
        flag = dds_get_aws_has_something_to_do_via_gui_flag_file()
        pathlib.Path(flag).touch()
        lg.a("user clicked cloud icon")

    def click_lbl_cnv(self, _):
        self.lbl_cnv.setText("checking")
        flag = dds_get_cnv_requested_via_gui_flag_file()
        pathlib.Path(flag).touch()
        lg.a("user clicked lbl_cnv")

    def click_chk_rerun(self, _):
        if self.chk_rerun.isChecked():
            # checked, so don't created do not rerun flag
            clr_ddh_do_not_rerun_flag_li()
        else:
            set_ddh_do_not_rerun_flag_li()

    def click_chk_b_maps(self, _):
        c = cfg_load_from_file()
        c['flags']['maps_en'] = int(self.chk_b_maps.isChecked())
        cfg_save_to_file(c)

    def click_btn_map_next(self, _):
        fol = str(ddh_get_folder_path_res())
        self.i_good_maps = (self.i_good_maps + 1) % self.n_good_maps
        lg.a(f'showing map #{self.i_good_maps}')
        now = str(datetime.datetime.now().strftime('%Y%m%d'))
        d = {
            0: f"{fol}/{now}_F_dtm.gif",
            1: f"{fol}/{now}_F_gom.gif",
            2: f"{fol}/{now}_F_mab.gif"
        }

        try:
            m = d[self.i_good_maps]
            if not os.path.exists(m):
                m = f"{fol}/error_maps.gif"
        except (Exception, ) as ex:
            lg.a(f'error: when next map => {ex}')
            m = f"{fol}/error_maps.gif"

        self.gif_map = QMovie(m)
        self.lbl_map.setMovie(self.gif_map)
        self.gif_map.start()
        self.map_filename = m

    def click_chk_plt_only_inside_water(self, _):
        from ddh.utils_graph import cached_read_csv
        # from ddh.utils_graph import process_graph_csv_data
        cached_read_csv.cache_clear()
        # process_graph_csv_data.cache_clear()
        p = LI_PATH_PLOT_ONLY_DATA_IN_WATER
        if self.chk_plt_only_inside_water.isChecked():
            pathlib.Path(p).touch()
        else:
            os.unlink(p)

    def click_graph_btn_reset(self):
        self.g.getPlotItem().enableAutoRange()
        process_n_graph(self)

    def click_graph_listview_logger_sn(self, _):
        process_n_graph(self)

    def click_graph_btn_next_haul(self):
        process_n_graph(self, r='hauls_next')

    def click_graph_lbl_haul_types(self, _):
        process_n_graph(self, r='hauls_labels')

    def click_graph_btn_paint_zones(self, _):
        process_n_graph(self)

    def click_graph_cb_switch_tp(self, _):
        process_n_graph(self)


def on_ctrl_c(signal_num, _):
    p = ddh_get_gui_closed_flag_file()
    pathlib.Path.touch(p, exist_ok=True)
    lg.a("closing DDS by ctrl + c")
    dds_kill_by_pid_file()
    lg.a("closing DDH by ctrl + c")
    lg.a(f"received exactly signal number {signal_num}")
    os._exit(0)
