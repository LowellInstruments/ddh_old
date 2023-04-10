import subprocess as sp
import time


def _check_temperature():
    c = "/usr/bin/vcgencmd measure_temp"
    rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)

    try:
        ans = rv.stdout
        print("debug: {} degrees Celsius".format(ans))

    except (Exception,) as ex:
        print("error: getting vcgencmd -> {}".format(ex))


if __name__ == "__main__":
    while True:
        _check_temperature()
        time.sleep(10)
