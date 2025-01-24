#!/usr/bin/env python3


import os
import time
from signal import pause
from gpiozero import Button

MS_100 = (1 / 10)
MS_10 = (1 / 100)
MS_1 = (1 / 1000)

PIN_BTN_1 = 16
PIN_BTN_2 = 20
PIN_BTN_3 = 21
b1 = Button(PIN_BTN_1, pull_up=True, bounce_time=MS_1)
b2 = Button(PIN_BTN_2, pull_up=True, bounce_time=MS_1)
b3 = Button(PIN_BTN_3, pull_up=True, bounce_time=MS_1)


def button1_pressed_cb():
    print('.')
    time.sleep(MS_10)
    global b1
    if b1.is_pressed:
        print('top')


def button2_pressed_cb():
    time.sleep(MS_10)
    global b2
    if b2.is_pressed:
        print('mid')


def button3_pressed_cb():
    time.sleep(MS_10)
    global b3
    if b3.is_pressed:
        print('low')


def main_test_box_buttons():
    os.system('clear')
    print('\nDDH hardware side buttons test v3')
    print('press Ctrl+C to quit')
    global b1
    global b2
    global b3
    b1.when_pressed = button1_pressed_cb
    b2.when_pressed = button2_pressed_cb
    b3.when_pressed = button3_pressed_cb
    pause()


if __name__ == '__main__':
    main_test_box_buttons()
