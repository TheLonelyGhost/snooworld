from dataclasses import dataclass
from typing import Dict, Optional

import requests

from snooworld import __version__
from snooworld.rate_limit import RateCounter

# This is a global variable to share across threads so when one thread updates the bearer token, they all reap the benefits. Keyed by username.
auth_tokens: Dict[str, "BearerTokenAuth"] = {}
rate_limiters: Dict[str, RateCounter] = {}


class TokenRefreshError(ValueError):  # TODO: Better base class than ValueError?
    pass


@dataclass
class TokenRefreshCreds(object):
    username: str
    password: str
    client_id: str
    secret_key: str


class BaseRedditClient(requests.Session):
    def __init__(self, *args, **kwargs):
        super(BaseRedditClient, self).__init__(*args, **kwargs)

        self.rate_limiter: Optional[RateCounter] = None

        self.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": f"python:org.grafeas.snooworld:v{__version__} (by u/personalopinions)",
            }
        )

        self._base_url = "https://www.reddit.com"
        self._response_callbacks = []

    def prepare_request(self, request, **kwargs):
        if request.url.startswith("/"):
            # Insert our base url by default
            request.url = self._base_url + request.url

        if self.rate_limiter:
            self.rate_limiter.throttle()

        for func in self._response_callbacks:
            request.register_hook("response", func)

        return super(BaseRedditClient, self).prepare_request(request, **kwargs)

    def _register_rate_limit_tracker(self):
        if not rate_limiters.get(self._tracking_key):
            rate_limiters[self._tracking_key] = RateCounter()
            self.rate_limiter = rate_limiters[self._tracking_key]

        def rate_limit_tracker(resp, *hook_args, **hook_kwargs):
            if resp.headers.get("x-ratelimit-used"):
                # Chances are the headers include all of the rate limiting stuff if this is given
                rate_used = int(float(resp.headers["x-ratelimit-used"]))
                rate_left = int(float(resp.headers["x-ratelimit-remaining"]))
                rate_reset_time = int(float(resp.headers["x-ratelimit-reset"]))

                # Update the ratelimit cross-thread object
                rate_limiters[self._tracking_key].update(
                    rate_used, rate_left, rate_reset_time
                )

            return resp

        self._response_callbacks.append(rate_limit_tracker)


class AnonymousClient(BaseRedditClient):
    def __init__(self, *args, **kwargs):
        self._tracking_key = ""
        super(AnonymousClient, self).__init__(*args, **kwargs)

        # This is invalid by design. Guaranteed not to overlap with an actual reddit username
        self._register_rate_limit_tracker()


class BearerTokenAuth(requests.auth.AuthBase):
    def __init__(self, token, refresh_token):
        self.token = token
        self.refresh_token = refresh_token

    def __call__(self, r):
        r.headers["Authorization"] = f"bearer {self.token}"
        return r


def is_invalid_bearer_token_response(resp: requests.models.Response) -> bool:
    if resp.status_code in (401, 403):
        return True

    # This space intentionally left open for detecting edge-cases where we need to refresh the bearer token

    return False


def is_bearer_token_request(request: requests.models.Request) -> bool:
    return str(request.url).endswith("/api/v1/access_token")


def is_bearer_token_response(resp: requests.models.Response) -> bool:
    for past_response in list(resp.history) + [resp]:
        if str(past_response.url).endswith(".reddit.com/api/v1/access_token"):
            return True

    return False


def add_new_bearer_token(tracking_key, bearer_token: BearerTokenAuth):
    # TODO: synchronize with other threads first
    auth_tokens[tracking_key] = bearer_token


def bearer_token_for(tracking_key) -> BearerTokenAuth:
    # TODO: synchronize with other threads first
    return auth_tokens.get(tracking_key, BearerTokenAuth(None, None))


class AuthenticatedClient(BaseRedditClient):
    _MAX_REAUTH_RETRIES: int = 2

    def __init__(self, username, password, client_id, secret_key, *args, **kwargs):
        super(AuthenticatedClient, self).__init__(*args, **kwargs)

        # Per the docs, authenticated requests should go here
        self._base_url = "https://oauth.reddit.com"
        self._refresh_counter = 0
        self._tracking_key = username

        # Hooks
        self._register_rate_limit_tracker()
        self._register_bearer_token_hook(
            username=username,
            password=password,
            client_id=client_id,
            secret_key=secret_key,
        )

    def _register_bearer_token_hook(self, username, password, client_id, secret_key):
        # We're defining this here so we can use some lexical scoping to involve
        # the Session object.
        def refresh_bearer_token(resp, *hook_args, **hook_kwargs):
            if is_bearer_token_response(resp):
                # Don't mess with recursion through this flow
                return resp

            if not is_invalid_bearer_token_response(resp):
                # Must be a valid response, so reset infinite loop detection and pass it through like normal
                self._refresh_counter = 0
                return resp

            if self._refresh_counter > self._MAX_REAUTH_RETRIES:
                # Retried twice (or more)
                raise TokenRefreshError(
                    "Found an infinite loop: Refreshing the bearer token works, but the resulting token appears to be invalid, triggering another refresh..."
                )

            # Attempt to refresh the bearer token
            self._refresh_counter += 1

            token = bearer_token_for(self._tracking_key)
            if token.refresh_token:
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token,
                }
            else:
                # If no refresh token, we have to re-send the username/password combo each time to refresh
                data = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                }

            r = self.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(client_id, secret_key),
                data=data,
            )
            r.raise_for_status()
            json = r.json()
            if not token.token:
                # It's falsey, so must not exist. Create one!
                token = BearerTokenAuth(json["access_token"], json.get("refresh_token"))
                add_new_bearer_token(self._tracking_key, token)
            else:
                # modify the token in-place, across threads
                token.token = json["access_token"]

            # Use this auth moving forward:
            self.auth = token
            # Apply this auth for the previously prepared request (this is how `requests` does it anyway)
            token(resp.request)

            # Retry the request with the new token
            return self.send(resp.request)

        self._response_callbacks.append(refresh_bearer_token)


class RedditClient(object):
    """A client that can be passed to models and methods, each deciding if it needs authentication or can be anonymous.
    """

    def __init__(self, token, secret, username, password):
        self._anonymous = AnonymousClient()

        self._authenticated = AuthenticatedClient(
            client_id=token, secret_key=secret, username=username, password=password
        )

    @property
    def anonymous(self):
        return self._anonymous

    @property
    def authenticated(self):
        return self._authenticated
