#!/usr/bin/env python3


def button1_pressed_cb():
    print('1')


def button2_pressed_cb():
    print('2')


def button3_pressed_cb():
    print('3')


b1 = Button(16, pull_up=True, bounce_time=0.1)
b2 = Button(20, pull_up=True, bounce_time=0.1)
b3 = Button(21, pull_up=True, bounce_time=0.1)
b1.when_pressed = button1_pressed_cb
b2.when_pressed = button2_pressed_cb
b3.when_pressed = button3_pressed_cb

pause()
