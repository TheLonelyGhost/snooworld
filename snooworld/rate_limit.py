import calendar
import threading
import time


class RateCounter(object):
    def __init__(self):
        # Per rate counter we want to lock the threads accessing that instance, not per thread locking _everything_.
        self.lock = threading.RLock()
        self.expire_time: int
        self.calls_used: int
        self.calls_left: int

        self.reset()

    def throttle(self):
        """Blocks all threads trying to make a request once
        we're near the rate limit

        Based on the info passed into the object, we sleep
        until the supposed time our rate limit expires.
        """
        with self.lock:
            if self.calls_left < 10 and self.expire_time > time.gmtime():
                time.sleep(max(self.expire_time - time.gmtime(), 1))
                self.reset()

    def update(self, used: int, left: int, time_left: int):
        """Takes API rate limit info from Reddit (possibly
        out of order) and updates a central tracker to figure
        out the most up-to-date information.
        """
        # We need to handle if given out of order (comes in [1,2,3,4] and
        # is evaluated [3,2,4,1]) and figuring out what the latest one is
        # based on the args.
        new_expire_time = calendar.timegm(time.gmtime()) + time_left + 3
        # 3 seconds more than Reddit's estimate for margin of error

        with self.lock:
            if new_expire_time not in range(self.expire_time - 5, self.expire_time + 5):
                # Different timespan so we'll opt for the timespan that resets
                # the furthest from now. This is likely to be the most up-to-date
                # information from Reddit.
                if new_expire_time > self.expire_time:
                    self.calls_used = used
                    self.calls_left = left
                    self.expire_time = new_expire_time
            elif self.calls_used < used:
                # We're within the same timespan (within 5 second margin of
                # error) so we'll only update the usage to the more pessimistic
                # value of the two.
                self.calls_used = used
                self.calls_left = left

    def reset(self):
        """Resets the tracked information to a value that will always lose out to info updated from Reddit.
        """
        with self.lock:
            self.calls_used = 0
            self.calls_left = 999  # Some high number
            self.expire_time = 0
