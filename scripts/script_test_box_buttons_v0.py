#!/usr/bin/env python3
import os
from signal import pause
from gpiozero import Button


def button1_pressed_cb():
    print('top')


def button2_pressed_cb():
    print('mid')


def button3_pressed_cb():
    print('bottom')


os.system('clear')
print('\nDDH hardware side buttons test v1')
print('press Ctrl+C to quit')
b1 = Button(16, pull_up=True, bounce_time=0.1)
b2 = Button(20, pull_up=True, bounce_time=0.1)
b3 = Button(21, pull_up=True, bounce_time=0.1)
b1.when_pressed = button1_pressed_cb
b2.when_pressed = button2_pressed_cb
b3.when_pressed = button3_pressed_cb

pause()
