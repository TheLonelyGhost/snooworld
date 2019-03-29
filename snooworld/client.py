import threading
from typing import Dict, Optional

import requests

from snooworld import __version__
from snooworld.rate_limit import RateCounter

# This is a global variable to share across threads so when one thread updates the bearer token, they all reap the benefits. Keyed by username.
auth_tokens: Dict[str, requests.auth.AuthBase] = {}
rate_limiters: Dict[str, RateCounter] = {}

lock = threading.RLock()


class TokenRefreshError(ValueError):  # TODO: Better base class than ValueError?
    pass


class BaseRedditClient(requests.Session):

    def __init__(self, *args, **kwargs):
        super(BaseRedditClient, self).__init__(*args, **kwargs)

        self.rate_limiter: Optional[RateCounter] = None

        self.headers.update({
            "Accept": "application/json",
            "User-Agent": f"python:org.grafeas.snooworld:v{__version__} (by u/personalopinions)",
        })

        self._base_url = "https://www.reddit.com"

    def prepare_request(self, request, **kwargs):
        if request.url.startswith('/'):
            # Insert our base url by default
            request.url = self._base_url + request.url

        if self.rate_limiter:
            # TODO: Enforce rate limiting wait times
            pass

        return super(BaseRedditClient, self).prepare_request(request, **kwargs)


class AnonymousClient(BaseRedditClient):
    def __init__(self, *args, **kwargs):
        super(AnonymousClient, self).__init__(*args, **kwargs)
        username = ''  # This is invalid by design. Guaranteed not to overlap with an actual reddit username

        if not rate_limiters.get(username):
            rate_limiters[username] = RateCounter()
            self.rate_limiter = rate_limiters[username]

        def rate_limit_tracker(resp, *hook_args, **hook_kwargs):
            if resp.headers.get('x-ratelimit-used'):
                # Chances are the headers include all of the rate limiting stuff if this is given
                rate_used = int(resp.headers["x-ratelimit-used"])
                rate_left = int(resp.headers["x-ratelimit-remaining"])
                rate_reset_time = int(resp.headers["x-ratelimit-reset"])

                # Update the ratelimit cross-thread object
                rate_limiters[username].update(rate_used, rate_left, rate_reset_time)

            return resp

        self.register_hook('response', rate_limit_tracker)


class BearerTokenAuth(requests.auth.AuthBase):
    def __init__(self, token, refresh_token):
        self.token = token
        self.refresh_token = refresh_token

    def __call__(self, r):
        r.headers['Authorization'] = f"bearer {self.token}"
        return r


def is_invalid_bearer_token_response(resp: requests.models.Response) -> bool:
    if resp.status_code == 401:
        return True

    # This space intentionally left open for detecting edge-cases where we need to refresh the bearer token

    return False


class AuthenticatedClient(BaseRedditClient):

    def __init__(self, token, secret, username, password, *args, **kwargs):
        super(AuthenticatedClient, self).__init__(*args, **kwargs)

        self._base_url = "https://oauth.reddit.com"  # Per the docs, authenticated requests should go here
        self._refresh_counter = 0

        refresh_url = "https://www.reddit.com/api/v1/access_token"  # Set here so we're sure the url checked to safeguard recursion is also used to make the call

        if not auth_tokens.get(username, BearerTokenAuth(None, None)).token:
            r = self.post(refresh_url,
                          auth=(token, secret),
                          data={"grant_type": "password",
                                "username": username,
                                "password": password})
            r.raise_for_status()
            json = r.json()
            auth_tokens[username] = BearerTokenAuth(json["access_token"], json.get("refresh_token"))
            self.auth = auth_tokens[username]

        if not rate_limiters.get(username):
            rate_limiters[username] = RateCounter()
            self.rate_limiter = rate_limiters[username]

        # We're defining this here so we can use some lexical scoping to involve
        # the Session object.
        def refresh_bearer_token(resp, *hook_args, **hook_kwargs):
            for past_response in (list(resp.history) + [resp]):
                # If refreshing the bearer token, don't recurse into refreshing the bearer token again. We're already doing that.
                if refresh_url == past_response.url:
                    return resp

            if not is_invalid_bearer_token_response(resp):
                # Must be a valid response, so reset infinite loop detection and pass it through like normal
                self._refresh_counter = 0
                return resp

            if self._refresh_counter > 3:
                raise TokenRefreshError('Found an infinite loop: Refreshing the bearer token works, but the resulting token appears to be invalid, triggering another refresh...')

            # Attempt to refresh the bearer token with the given refresh token
            self._refresh_counter += 1

            if auth_tokens[username].refresh_token:
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": auth_tokens[username].refresh_token,
                }
            else:
                # If no refresh token, we have to re-send the username/password combo each time to refresh
                data = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                }

            r = self.post(refresh_url, auth=(token, secret), data=data)
            r.raise_for_status()
            auth_tokens[username].token = r.json()["access_token"]

            # Retry the request with the new token
            return self.send(resp.request)

        def rate_limit_tracker(resp, *hook_args, **hook_kwargs):
            if resp.headers.get('x-ratelimit-used'):
                # Chances are the headers include all of the rate limiting stuff if this is given
                rate_used = int(resp.headers["x-ratelimit-used"])
                rate_left = int(resp.headers["x-ratelimit-remaining"])
                rate_reset_time = int(resp.headers["x-ratelimit-reset"])

                # Update the ratelimit cross-thread object
                self.rate_limiter.update(rate_used, rate_left, rate_reset_time)

            return resp

        self.register_hook('response', refresh_bearer_token)


class RedditClient(object):
    """A client that can be passed to models and methods, each deciding if it needs authentication or can be anonymous.
    """

    def __init__(self, token, secret, username, password):
        self._anonymous = AnonymousClient()
        self._authenticated = AuthenticatedClient(token, secret, username, password)

    @property
    def anonymous(self):
        return self._anonymous

    @property
    def authenticated(self):
        return self._authenticated
