import urllib.request
from urllib.parse import urlparse


def check_internet(
    url: str = "http://www.google.com", timeout: int = 15, check: bool = False
) -> bool:
    """
    Check for internet connectivity by attempting to reach a known URL.

    This function caches the result on the first call. Subsequent calls will reuse the cached value
    unless the process is restarted.

    :param url: URL to test for connectivity. Defaults to "http://www.google.com".
    :param timeout: The number of seconds to wait before timing out. Defaults to 15.
    :param check: If True and the connection check fails, raise a ConnectionError.

    :return bool: True if the connection succeeded, False otherwise.

    :raises ConnectionError: If `check` is True and the connection fails.

    Example:
        >>> check_internet()
        True
        >>> check_internet(check=True)
        ConnectionError: No internet connection
    """
    exc: Exception | None = None
    if not hasattr(check_internet, "response"):
        try:
            urllib.request.urlopen(url, timeout=timeout)
            # check_internet.response = True
            setattr(check_internet, "response", True)
        except Exception as e:
            setattr(check_internet, "response", False)
            exc = e  # - corrected
    if check and not getattr(check_internet, "response", False):
        raise ConnectionError("No internet connection") from exc
    result = getattr(check_internet, "response", False)
    return bool(result)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
