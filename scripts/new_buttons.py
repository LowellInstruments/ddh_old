from signal import pause

import RPi.GPIO as GPIO

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
    bouncetime=100
)
GPIO.add_event_detect(
    38,
    GPIO.FALLING,
    callback=b2_cb,
    bouncetime=100
)
GPIO.add_event_detect(
    40,
    GPIO.FALLING,
    callback=b3_cb,
    bouncetime=100
)


pause()
GPIO.cleanup() # Clean up
