from .block import Block

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
            "signature": "8XUZi9uGDRNscFfoaycQblSsb7bpsw7J2AV5vt6qXZqq3aCQW6g4cI+fKlu1GuorSSHxt/h9vjsZa7O9Y2+bUw==",
            "time": "1631839469.7635121",
            "hash": "97f70d8a0991b87f15d50e259792a83c337efd8e3f8dc041a134ccbc80787421",
        }
    ],
    "hash": "c81b57534931bb1d713abcc2ccf2a4306bf0744ed0aba9cf54c935c33b665130",
    "signature": "y32tDYZpqpNocSBgq2Yn+/dgNQzzeyIHmQar/YzrQol0UQR9QAirjI8UznYEnkWtgl+isRDHwXpGgq2ma2JCyQ==",
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

    def get_balance(self, address: str):
        bal = 0
        for block in self.chain:
            for t in block.transactions:
                if t.sender == address:
                    bal -= t.amount
                if t.receiver == address:
                    bal += t.amount

    def add_genesis_block(self):
        genesis_block = Block.from_json(**GENESIS_BLOCK_DATA)
        self.chain.append(genesis_block)
