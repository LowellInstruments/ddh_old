#!/usr/bin/env python3


import os
import time
from signal import pause
from gpiozero import Button


TIME_LO_S = .5
TIME_DB_S = .001
g_last_t = 0


def _cb(s):
    t = time.perf_counter()
    global g_last_t
    if t > g_last_t + TIME_LO_S:
        print(s)
        g_last_t = t


def button1_pressed_cb():
    _cb('top')

def button2_pressed_cb():
    _cb('mid')

def button3_pressed_cb():
    _cb('bottom')


os.system('clear')
print('\nDDH hardware side buttons test v2')
print('press Ctrl+C to quit')
b1 = Button(16, pull_up=True, bounce_time=TIME_DB_S)
b2 = Button(20, pull_up=True, bounce_time=TIME_DB_S)
b3 = Button(21, pull_up=True, bounce_time=TIME_DB_S)
b1.when_pressed = button1_pressed_cb
b2.when_pressed = button2_pressed_cb
b3.when_pressed = button3_pressed_cb

pause()
