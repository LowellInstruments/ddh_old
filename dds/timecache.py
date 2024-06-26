from cacheout import Cache
import time


TIM_CACHE_MAX_SIZE = 1024
_g_timecache = Cache(maxsize=TIM_CACHE_MAX_SIZE,
                     ttl=0, timer=time.time, default=None)


def query_is_it_time_to(k):
    return k not in _g_timecache


def its_time_to_so_annotate_it(k, t):
    if t == 0:
        return
    _g_timecache.add(k, k, ttl=t)


def is_it_time_to(k, t):
    if query_is_it_time_to(k):
        its_time_to_so_annotate_it(k, t)
        return True
    # not enough time has passed since last occurrence of this
    return False


def main():
    v = is_it_time_to("test", 0)
    print(v)
    v = is_it_time_to("test", 0)
    print(v)
    time.sleep(3)
    v = is_it_time_to("test", 0)
    print(v)


if __name__ == "__main__":
    main()
