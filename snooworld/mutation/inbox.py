from typing import Iterable

from snooworld.client import RedditClient
from snooworld.models import Message


class MessageMutator(object):
    def __init__(self, http: RedditClient):
        self.http = http.authenticated

    def read(self, messages: Iterable[Message]):
        data = {
            "id": ",".join([f"{m.kind}_{m.id}" for m in messages]),
        }
        r = self.http.post("/api/read_message", data=data)
        r.raise_for_status()

    def unread(self, messages: Iterable[Message]):
        data = {
            "id": ",".join([f"{m.kind}_{m.id}" for m in messages]),
        }
        r = self.http.post("/api/unread_message", data=data)
        r.raise_for_status()
