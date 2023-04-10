from gpiozero import Button
import time


button_a = Button(16, pull_up=True)
button_b = Button(20, pull_up=True)
button_c = Button(21, pull_up=True)


def button_a_held_cb():
    print("held button A")


def button_a_pressed_cb():
    print("pressed button A")


def button_a_released_cb():
    print("released button A")


def button_b_held_cb():
    print("held button B")


def button_b_pressed_cb():
    print("pressed button B")


def button_b_released_cb():
    print("released button B")


def button_c_held_cb():
    print("held button C")


def button_c_pressed_cb():
    print("pressed button C")


def button_c_released_cb():
    print("released button C")


button_a.when_held = button_a_held_cb
button_a.when_pressed = button_a_pressed_cb
button_a.when_released = button_a_released_cb
button_b.when_held = button_b_held_cb
button_b.when_pressed = button_b_pressed_cb
button_b.when_released = button_b_released_cb
button_c.when_held = button_c_held_cb
button_c.when_pressed = button_c_pressed_cb
button_c.when_released = button_c_released_cb


while True:
    # callbacks will be called
    print(".")
    time.sleep(1)
