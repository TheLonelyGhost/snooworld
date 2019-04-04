from snooworld.models import Comment


def test_comment_structure(client):
    c = Comment.from_id(http=client, post_id="8vz4wd", comment_id="e1rin0h")

    assert len(c.replies) > 0


def test_comment_json_deserialization():
    # TODO
    pass
