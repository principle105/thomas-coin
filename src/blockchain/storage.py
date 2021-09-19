import _pickle as pickle
from config import BLOCK_PATH


def get_block_data():
    with open(BLOCK_PATH, "rb") as f:
        return pickle.load(f)


def dump_block_data(data: list):
    with open(BLOCK_PATH, "wb") as f:
        pickle.dump(data, f, protocol=2)
