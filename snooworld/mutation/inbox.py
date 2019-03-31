from typing import Iterable

from snooworld.models import Message
from snooworld.mutation._base import BaseMutator


class MessageMutator(BaseMutator):
    def read(self, messages: Iterable[Message]):
        data = {"id": ",".join([f"{m.kind}_{m.id}" for m in messages])}
        r = self.http.post("/api/read_message", data=data)
        r.raise_for_status()

    def unread(self, messages: Iterable[Message]):
        data = {"id": ",".join([f"{m.kind}_{m.id}" for m in messages])}
        r = self.http.post("/api/unread_message", data=data)
        r.raise_for_status()
