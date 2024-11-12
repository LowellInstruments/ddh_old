import threading
import time
from signal import pause
from gpiozero import Button
from mat.utils import linux_is_rpi
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_PRESSED_BUTTON_2,
    STATE_DDS_PRESSED_BUTTON_1,
)


def _th_gpio_box_buttons_old():
    if not linux_is_rpi():
        return

    def button1_pressed_cb():
        _u(STATE_DDS_PRESSED_BUTTON_1)

    def button2_pressed_cb():
        _u(STATE_DDS_PRESSED_BUTTON_2)

    def button3_pressed_cb():
        pass

    b1 = Button(16, pull_up=True, bounce_time=0.1)
    b2 = Button(20, pull_up=True, bounce_time=0.1)
    b3 = Button(21, pull_up=True, bounce_time=0.1)
    b1.when_pressed = button1_pressed_cb
    b2.when_pressed = button2_pressed_cb
    b3.when_pressed = button3_pressed_cb
    pause()


TIME_LO_S = .5
TIME_DB_S = .001
g_last_t = 0


def _th_gpio_box_buttons():
    def _cb(s):
        t = time.perf_counter()
        global g_last_t
        if t > g_last_t + TIME_LO_S:
            print(s)
            g_last_t = t

    def button1_pressed_cb():
        _u(STATE_DDS_PRESSED_BUTTON_1)

    def button2_pressed_cb():
        _u(STATE_DDS_PRESSED_BUTTON_2)

    def button3_pressed_cb():
        pass

    b1 = Button(16, pull_up=True, bounce_time=TIME_DB_S)
    b2 = Button(20, pull_up=True, bounce_time=TIME_DB_S)
    b3 = Button(21, pull_up=True, bounce_time=TIME_DB_S)
    b1.when_pressed = button1_pressed_cb
    b2.when_pressed = button2_pressed_cb
    b3.when_pressed = button3_pressed_cb
    pause()


def dds_create_buttons_thread():
    bth = threading.Thread(target=_th_gpio_box_buttons)
    bth.start()
