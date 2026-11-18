from urllib.parse import urlsplit, urlunsplit


def sanitize_endpoint(value: str) -> str:
    parts = urlsplit(value)
    host = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, host, "", "", ""))
