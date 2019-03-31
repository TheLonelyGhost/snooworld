from snooworld.models import UserFlair
from snooworld.mutation._base import BaseMutator


class FlairMutator(BaseMutator):
    def set_user_flair(self, flair: UserFlair):
        data = {
            "api_type": "json",
            "name": flair.username,
            "css_class": flair.css_class,
            "text": flair.text,
        }
        r = self.http.post(f"/r/{flair.subreddit}/api/flair", data=data)
        r.raise_for_status()
