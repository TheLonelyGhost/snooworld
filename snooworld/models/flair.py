from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from snooworld.client import RedditClient
from snooworld.models._base import MalformedRedditResponse, _unwrap_listing


@dataclass
class UserFlair(object):
    username: str
    subreddit: str
    css_class: str
    text: str = field(default="")
    template_id: Optional[str] = field(default=None)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "UserFlair":
        """A factory method for parsing the Reddit response JSON into a usable data object

        This is separated from `from_comment()` so we can test the retrieval via HTTP
        separately from how it loads a JSON payload into the data structure.
        """
        if json["kind"] != "t1":
            raise ValueError("Must be a Comment type JSON object")

        obj = json["data"]

        return cls(
            username=obj["author"],
            subreddit=obj["subreddit"],
            css_class=obj["author_flair_css_class"],
            text=obj["author_flair_text"],
            template_id=obj["author_flair_template_id"],
        )

    @classmethod
    def from_comment(
        cls, post_id: str, comment_id: str, http: RedditClient
    ) -> "UserFlair":
        """The primary factory method for reading user flair.

        Unfortunately, Reddit needs an example comment the user has made to view the flair
        they have assigned to them for the given subreddit. Setting it for the subreddit is
        no problem (if you're a mod) without this context, but reading it requires more.

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
