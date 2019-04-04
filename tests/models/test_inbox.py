from snooworld.models import Inbox


def test_inbox(client):
    messages = list(Inbox.all(http=client))

    assert len(messages) > 0
