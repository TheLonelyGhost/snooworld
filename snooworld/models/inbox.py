from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

from snooworld.client import RedditClient
from snooworld.models._base import _unwrap_listing


@dataclass
class Message(object):
    """A message that exists in the inbox
    """
    id: str
    subject: str
    author: Optional[str]  # mail from the mods makes this `None` sometimes, and that's okay
    body: str
    context: Optional[str]  # If a comment reply, this is where we'd find the link to the comment

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> 'Message':
        if not json['kind'] == 't1':
            raise ValueError('Requires JSON to be for a Message')

        json = json['data']

        return cls(
            id=json['id'],
            author=json['author'],
            subject=json['subject'],
            body=json['body'],
            context=json['context'],
        )

    @classmethod
    def unread_inbox(cls, http: RedditClient) -> 'Iterator[Message]':
        query_data = {
            'mark': 'false',
            'limit': '100',
        }
        inbox: List[Dict] = []

        # if we haven't reached the end after 30 pages,
        # let's take a break and require us to call the
        # method again.
        for _ in range(30):
            r = http.authenticated.get("/message/unread.json", query={"mark": "false", "limit": "100"})
            r.raise_for_status()
            json = r.json()
            inbox += _unwrap_listing(json)

            if not json['data']['after']:
                break

            query_data['after'] = json['data']['after']

        # Oldest message first
        return reversed([cls.from_json(m) for m in inbox])
