import os

import pytest  # type: ignore

from snooworld.client import RedditClient
from snooworld.models import Comment


@pytest.fixture
def client():
    return RedditClient(
        token=os.environ["REDDIT_TOKEN"],
        secret=os.environ["REDDIT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
    )


def test_comment_structure(client):
    c = Comment.from_id(http=client, post_id="8vz4wd", comment_id="e1rin0h")

    assert len(c.replies) > 0
