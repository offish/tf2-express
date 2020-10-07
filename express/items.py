#import requests
import json

from .methods import read, write, request
#from .utils import get_defindex

PATH = 'express/json/items.json'


# Skal brukes i panel
def add(name: str) -> None:
    data = read(PATH)
    data[name]
    write(PATH, data)


# Skal brukes i panel
def remove(name: str) -> None:
    data = read(PATH)
    
    if name in data:
        data.remove(name)
        write(PATH, data)


def get_items() -> dict:
    return read(PATH)
