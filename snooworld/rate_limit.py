import threading
import time


class RateCounter(object):
    def __init__(self):
        # Per rate counter we want to lock the threads accessing that instance, not per thread locking _everything_.
        self.lock = threading.RLock()

        self.reset()

    def enqueue_call(self):
        with self.lock:
            # TODO: wait until we can make another call
            pass

    def update(self, used: int, left: int, time_left: int):
        with self.lock:
            # TODO: Handle if given out of order (comes in [1,2,3,4] and is evaluated [3,2,4,1]) and figuring out what the latest one is based on the args.
            # NOTE: May be tricky if we have a rate limit reset in the middle of things
            self.calls_used = used
            self.calls_left = left
            self.expire_time = time.gmtime() + time_left + 3  # 3 seconds for margin of error

    def reset(self):
        with self.lock:
            self.calls_used = 0
            self.calls_left = 999  # Some high number
            self.expire_time = 0
