from functools import lru_cache
from .tree import Leaf
from base64 import b64encode
from constants import CURVE


def get_lottery_number(address):
    comp = b64encode(address.encode())[1:]
    r = int.from_bytes(comp, "big")
    return r / CURVE.order


# Caching to prevent having to recompute winner
@lru_cache(maxsize=1)
def find_winner(tree: Leaf, n: int):
    search_number = n * tree.value
    winner = tree.search(search_number)
    return winner


def do_lottery(chain_state):
    if len(chain_state.validators) == 0:
        return None

    # Creating sortition tree
    tree = Leaf.plant_tree(chain_state.validators)
    # Finding winner from lottery number
    return find_winner(tree, chain_state.lottery_number)
