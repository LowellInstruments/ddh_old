from cacheout import Cache
import time


TIM_CACHE_MAX_SIZE = 1024
_g_timecache = Cache(
    maxsize=TIM_CACHE_MAX_SIZE,
    ttl=0,
    timer=time.time,
    default=None
)


def annotate_time_this_occurred(k, t):
    if t <= 0:
        return
    _g_timecache.add(k, k, ttl=t)


def delete_annotation(k):
    _g_timecache.delete(k)


def delete_all_annotations_by_mask(mask):
    for k in _g_timecache.keys():
        if k.startswith(mask):
            _g_timecache.delete(k)


def delete_all_annotations():
    for k in _g_timecache.keys():
        _g_timecache.delete(k)


def is_it_time_to(k, t, annotate=True):
    if not _g_timecache.has(k):
        if annotate:
            annotate_time_this_occurred(k, t)
        return True

    # not enough time passed since last occurrence of this
    return False


# test
if __name__ == '__main__':
    annotate_time_this_occurred('k', 10)
    delete_all_annotations_by_mask('k')
    rv = is_it_time_to('k', 0, annotate=False)
    print(rv)

