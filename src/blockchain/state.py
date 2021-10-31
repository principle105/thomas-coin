import time
from .block import Block
from wallet import Other_Wallet
from consensus import get_lottery_number
from constants import INITIAL_NUMBER


class State:
    def __init__(self):
        self.wallets = {}  # "address": wallet

        self.validators = {}  # "address": Stake

        self.length = 0

        self.last_block: Block = None

        self.lottery_number = INITIAL_NUMBER

    def add_block(self, block: Block):
        self.length += 1
        self.last_block = block

        # Updating lottery number with block forger
        self.lottery_number = get_lottery_number(block.forger)

        total_tips = 0

        for t in block.transactions:
            receiver = self.get_wallet(t.receiver)

            # Updating the wallet balance
            if t.sender != "GENESIS":
                sender = self.get_wallet(t.sender)
                sender.balance -= t.amount
                sender.nonce += 1

            receiver.balance += t.amount

            # Adding transaction tip to forger
            total_tips += t.tip

        if block.forger != "GENESIS":
            # TODO: Wait 15 days before adding balance to forger
            forger = self.get_wallet(block.forger)
            forger.balance += block.reward + total_tips

    def get_wallet(self, address: str):
        if address not in self.wallets:
            # Creating a new wallet
            self.wallets[address] = Other_Wallet(address)

        return self.wallets[address]

    # Based off: https://github.com/ethereum/EIPs/blob/master/EIPS/eip-2.md
    def calculate_next_difficulty(self) -> int:
        """Calculates the difficulty of the next block"""
        return int(
            self.last_block.difficulty
            + self.last_block.difficulty
            // 2048
            * max(1 - (time.time() - self.last_block.timestamp) // 10, -99)
            + int(2 ** ((self.length // 100000) - 2))
        )
