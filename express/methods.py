from json import load, dump


def read(path: str) -> dict:
    with open(path, 'r') as file:
        return load(file)


def write(path: str, data: dict):
    with open(path, 'w') as file:
        dump(data, file)
