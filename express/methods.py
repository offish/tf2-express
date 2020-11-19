from json import load, loads, dump

import requests

FAILURE = {'success': False}

def request(url: str, payload: dict = {}, headers: dict = {}) -> dict:
    r = requests.get(url, params=payload, headers=headers)
    
    try:
        return loads(r.text)
    except ValueError:
        return {**FAILURE, 'status_code': r.status_code, 'text': r.text}
