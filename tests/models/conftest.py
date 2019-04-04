import os

import pytest  # type: ignore

from snooworld.client import RedditClient


@pytest.fixture(scope="session")
def client():
    obj = RedditClient(
        token=os.environ["REDDIT_TOKEN"],
        secret=os.environ["REDDIT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
    )
    obj.authenticated._MAX_REAUTH_RETRIES = 1
    return obj
