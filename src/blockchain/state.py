from .block import Block


class State:
    def __init__(self):
        self.wallets = {}  # "address": balance
        self.length = 0
        self.last_block: Block = None

    def add_block(self, block: Block):
        pass

    def get_wallet(self, address: str):
        if address == self.wallets:
            return self.wallet[address]
        return None
