import time
import os

DOG_GUI = '/dev/shm/dog_gui.txt'


def gui_dog_clear():
    if os.path.exists(DOG_GUI):
        os.unlink(DOG_GUI)


def gui_dog_touch():
    # written by main_ddh
    with open(DOG_GUI, 'w') as f:
        now = int(time.perf_counter())
        f.write(str(now))


def gui_dog_get():
    # read by main_ddh_controller
    try:
        with open(DOG_GUI) as f:
            return int(f.readline())
    except (Exception, ):
        # disabled
        return 0


if __name__ == '__main__':
    time.sleep(3)
    gui_dog_touch()
    v = gui_dog_get()
    print(v)
