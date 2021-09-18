from .block import Block
from hashlib import sha256

GENESIS_BLOCK_DATA = {
    "index": "0",
    "prev": "0",
    "forger": "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6 ",
    "timestamp": "1631749808.558269",
    "transactions": [
        {
            "sender": "971a12a0d1c9068167226ff46eca48b2db547206e2adef193db7596cb30578a1fef2907db56dfb534efafd98776b77f13f74beee7c2b1f4d943f20cda6d31aff",
            "receiver": "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6",
            "amount": 1000,
            "tip": 0,
            "signature": "Stkd9WsC5+6fvZcR2clRPnysZJPD6Tam9LT5r4wybnbRS6QCB0/ExixORXWAwmgzyOOv364U08QE4YNcjHm9PQ==",
            "timestamp": "1631890525.674031",
            "hash": "7e1e4b2a9cf92501514dc4afd207917489912bf77122f931f7b19b8716465863",
        }
    ],
    "hash": "0fb4e9f2faada279c7c641eaeb8ffa52e8e3d75ae50f75b284e5d21c1acfd321",
    "signature": "RTWyryY82uhADCP0L3jFu8j8XibyOaqDN/DHWvRthh73zpaD270CnM+IhSSQUjZakpp7iwQn+it/GUkA5zUglw==",
}


class Blockchain:
    def __init__(self, chain: list[Block] = [], pruned: bool = False):
        self.chain = chain
        self.pruned = pruned

    def create_new_block(self, forger: str):
        """
        forger: public key of the block forger
        """

    def add_block(self, block: Block):

        # Checking if the block has a signature
        if block.signature is None:
            raise Exception("The block is not signed")

        # Checking if the block is valid
        block.validate(self)

        self.chain.append(block)

    def verify(self, address, public_key):
        print(
            "T"
            + sha256(
                sha256(public_key.encode("utf-8")).hexdigest().encode("utf-8")
            ).hexdigest()[-40:]
        )
        print("\n")
        print(address)
        return (
            "T"
            + sha256(
                sha256(public_key.encode("utf-8")).hexdigest().encode("utf-8")
            ).hexdigest()[-40:]
            == address
        )

    def get_balance(self, address: str):
        bal = 0
        for block in self.chain:
            for t in block.transactions:
                if self.verify(address, t.sender):
                    bal -= t.amount
                if t.receiver == address:
                    bal += t.amount
        return bal

    def add_genesis_block(self):
        genesis_block = Block.from_json(**GENESIS_BLOCK_DATA)
        self.chain.append(genesis_block)
