import json
from config import BLOCK_PATH


def get_block_data(block_index: int):
    with open(f"{BLOCK_PATH}/{block_index}.json", "r") as f:
        data = json.load(f)
    return data


def dump_block_data(block_index: int, data: dict):
    with open(f"{BLOCK_PATH}/{block_index}.json", "w") as f:
        json.dump(data, f)
