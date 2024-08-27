import time
import os

DOG_GUI = '/dev/shm/dog_gui.txt'


def gui_dog_clear():
    if os.path.exists(DOG_GUI):
        os.unlink(DOG_GUI)


def gui_dog_touch():
    with open(DOG_GUI, 'w') as f:
        now = int(time.perf_counter())
        f.write(str(now))


def gui_dog_get():
    try:
        with open(DOG_GUI) as f:
            return int(f.readline())
    except (Exception, ) as ex:
        # disabled
        return 0


if __name__ == '__main__':
    time.sleep(3)
    gui_dog_touch()
    v = gui_dog_get()
    print(v)
