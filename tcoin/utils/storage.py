import json
import os

from tcoin.config import storage_path


def _get_storage_path(name: str):
    return f"{storage_path}/{name}.json"


def load_storage_file(name: str, default={}):
    path = _get_storage_path(name)

    if not os.path.exists(path):
        return default

    with open(path, "r") as f:
        return json.load(f)


def save_storage_file(name: str, data):
    path = _get_storage_path(name)

    if not os.path.exists(storage_path):
        os.mkdir(storage_path)

    with open(path, "w") as f:
        return json.dump(data, f)
