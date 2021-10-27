from functools import lru_cache
from .sum_tree import Sum_Tree
from base64 import b64encode
from constants import CURVE


def get_lottery_number(address):
    comp = b64encode(address.encode())[1:]
    r = int.from_bytes(comp, "big")
    return r / CURVE.order


# Caching to prevent having to recompute winner
@lru_cache(maxsize=1)
def find_winner(tree: Sum_Tree, n: int):
    search_number = n * tree.sum
    winner = tree.search(search_number)
    return winner


def do_lottery(chain_state, address):
    wallets = chain_state.wallets
    data = {w: wallets[w].balance for w in wallets}
    print("DATA", data)

    tree = Sum_Tree.from_json(data)
    n = get_lottery_number(address)
    return find_winner(tree, n)
