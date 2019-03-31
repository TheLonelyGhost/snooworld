from typing import Any, Dict, List


class MalformedRedditResponse(ValueError):
    def __init__(self, url, method: str = "GET"):
        msg = f"Reddit gave an unexpected format for the response. To see what happened, {method.upper()} {url}"
        super(MalformedRedditResponse, self).__init__(msg)


def _unwrap_listing(json: Dict[str, Any]) -> List[Dict[str, Any]]:
    if json["kind"] != "Listing":
        raise ValueError("Object is not a Listing data structure")

    return json["data"]["children"]
