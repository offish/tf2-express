from json import loads

from requests import get


def request(url: str, payload: dict = {}, headers: dict = {}) -> dict:
    r = get(url, params=payload, headers=headers)

    try:
        return loads(r.text)
    except ValueError:
        return {"success": False, "status_code": r.status_code, "text": r.text}
