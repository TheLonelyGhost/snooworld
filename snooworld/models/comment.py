from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from snooworld.client import RedditClient
from snooworld.models._base import MalformedRedditResponse, _unwrap_listing


@dataclass
class Comment(object):
    subreddit: str
    author: str
    post_id: str
    parent_id: Optional[str]
    replies: List["Comment"]

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "Comment":
        """A factory method for parsing the Reddit response JSON into a usable data object

        This is separated from `from_id()` so we can test the retrieval via HTTP
        separately from how it loads a JSON payload into the data structure.
        """
        if json["kind"] != "t1":
            raise ValueError("Must be a Comment type JSON object")

        obj = json["data"]

        if not obj["link_id"].startswith("t3_"):
            raise ValueError("")

        replies = []
        for comment in _unwrap_listing(obj["replies"]):
            replies.append(cls.from_json(comment))

        return cls(
            subreddit=obj["subreddit"],
            author=obj["author"],
            post_id=obj["link_id"][3:],
            parent_id=obj["parent_id"][3:]
            if str(obj["parent_id"]).startswith("t1_")
            else None,
            replies=replies,
        )

    @classmethod
    def from_id(cls, post_id: str, comment_id: str, http: RedditClient) -> "Comment":
        """The primary factory method for reading comment information.

        To retrieve the comment info, Reddit also requires context of the post upon which
        the comment was made. Yay. (>_<)
        """
        url = f"https://www.reddit.com/comments/{post_id}/some-ignored-post-title-here/{comment_id}.json"
        r = http.anonymous.get(url)
        r.raise_for_status()
        json = r.json()

        # Because, for some reason, Reddit replies with a tuple (list with 2 items)
        # containing the post information at [0] and the comment info we seek at
        # index [1].
        if not isinstance(json, list) or len(json) < 2:
            raise MalformedRedditResponse(url, "GET")

        # Reddit also wraps listings as their own object type. So a list of posts
        # would be returned as a JSON object with its own "kind" and the data within
        # it would be the actual list. Therefore, we unwrap it.
        try:
            json = _unwrap_listing(json[1])[0]
        except (KeyError, ValueError):
            raise MalformedRedditResponse(url, "GET")

        return cls.from_json(json)
