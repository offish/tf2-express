from json import load, loads, dump
import requests

FAILURE = {'success': False}

def read(path: str) -> dict:
    with open(path, 'r') as file:
        return load(file)


def write(path: str, data: dict):
    with open(path, 'w') as file:
        dump(data, file)


def add(trade: dict):
    path = 'express/json/trades.json'
    data = read(path)
    data.append(trade)
    write(path, data)


def request(url: str, payload: dict = {}, headers: dict = {}) -> dict:
    r = requests.get(url, params=payload, headers=headers)
    
    try:
        return loads(r.text)
    except ValueError:
        return {**FAILURE, 'status_code': r.status_code, 'text': r.text}
