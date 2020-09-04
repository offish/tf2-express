from .methods import read, write

PATH = 'express/json/trades.json'

def add(trade: dict):
    data = read(PATH)
    data.append(trade)
    write(PATH, data)

