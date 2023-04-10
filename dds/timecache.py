from cacheout import Cache
import time


TIM_CACHE_MAX_SIZE = 1024
_g_timecache = Cache(maxsize=TIM_CACHE_MAX_SIZE, ttl=0, timer=time.time, default=None)


def its_time_to(k, t):
    if k in _g_timecache:
        return False
    _g_timecache.add(k, k, ttl=t)
    return True


def main():
    v = its_time_to("test", 3)
    print(v)
    v = its_time_to("test", 3)
    print(v)
    time.sleep(3)
    v = its_time_to("test", 3)
    print(v)


if __name__ == "__main__":
    main()
