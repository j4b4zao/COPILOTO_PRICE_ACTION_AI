"""Read and decode quote responses from an injected HTTP opener."""

from http.client import BadStatusLine, IncompleteRead
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from external_context.providers._quote_json import decode_quote_json


def fetch_quote_json(opener, endpoint: str, *, symbol: str, api_key: str, timeout: float):
    query = urlencode({"symbol": symbol, "apikey": api_key})
    request = Request(
        f"{endpoint}?{query}",
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=timeout)
        try:
            raw = response.read()
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except HTTPError as exc:
        try:
            exc.close()
        except OSError:
            # The quote is already unavailable even if cleanup fails.
            pass
        return None
    except (OSError, BadStatusLine, IncompleteRead):
        return None

    try:
        return decode_quote_json(raw)
    except (ValueError, RecursionError):
        return None
