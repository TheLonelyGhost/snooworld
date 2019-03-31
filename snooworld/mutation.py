from typing import Iterable

from snooworld.client import RedditClient
from snooworld.models import Message


def mark_messages_as_read(http: RedditClient, msgs: Iterable[Message]):
    data = {
        "id": ",".join([f"{m.kind}_{m.id}" for m in msgs])
    }
    r = http.authenticated.post('/api/read_message', data=data)
    r.raise_for_status()


def mark_message_as_read(http: RedditClient, msg: Message):
    return mark_messages_as_read(http, [msg])
