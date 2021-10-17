from .block import Block
from wallet import Other_Wallet


class State:
    def __init__(self):
        self.wallets = {}  # "address": balance

        self.validators = {}  # "address": amount

        self.length = 0

        self.last_block: Block = None

    def add_block(self, block: Block):
        self.length += 1
        self.last_block = block

        for t in block.transactions:
            sender = self.get_wallet(t.sender)
            receiver = self.get_wallet(t.receiver)

            # Updating the wallet balance
            sender.balance -= t.amount
            receiver.balance += t.amount + t.tip

    def get_wallet(self, address: str):
        if address not in self.wallets:
            # Creating a new wallet
            self.wallets[address] = Other_Wallet(address)

        return self.wallets[address]
