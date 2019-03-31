from snooworld.client import RedditClient


class BaseMutator(object):
    def __init__(self, http: RedditClient):
        self.http = http.authenticated
