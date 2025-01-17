#!/usr/bin/env python3
import os
from signal import pause
import RPi.GPIO as GPIO


BOUNCE_TIME_MS = 1000


def b1_cb(_): print('top')
def b2_cb(_): print('mid')
def b3_cb(_): print('low')


GPIO.setwarnings(False)
# use physical pin numbering
GPIO.setmode(GPIO.BOARD)


GPIO.setup(36, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(38, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(40, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(
    36,
    GPIO.FALLING,
    callback=b1_cb,
    bouncetime=BOUNCE_TIME_MS
)
GPIO.add_event_detect(
    38,
    GPIO.FALLING,
    callback=b2_cb,
    bouncetime=BOUNCE_TIME_MS
)
GPIO.add_event_detect(
    40,
    GPIO.FALLING,
    callback=b3_cb,
    bouncetime=BOUNCE_TIME_MS
)


def main_test_box_buttons():
    os.system('clear')
    print('\nDDH hardware side buttons test v3_NEW')
    print('press Ctrl+C to quit')
    print('')
    pause()
    GPIO.cleanup()


if __name__ == '__main__':
    main_test_box_buttons()
