try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from blockchain import Blockchain, Block
from wallet import Wallet
from transaction import Transaction
from os import getenv
import time

if __name__ == "__main__":
    owner = Wallet(getenv("OWNER_PRIVATE_KEY"))

    other = Wallet("1ef98e260c70ae196079655392461226c42778b8373ba9780e497272e47d53dc")

    chain = Blockchain()

    print(chain.blocks)

    for _ in range(20):
        # sending coins
        b = Block(len(chain.blocks), chain.blocks[-1].hash)
        if len(chain.blocks) == 1:

            t = Transaction(owner.public_key, other.address, 1, 0)

            t.sign(owner)

            b.append_transaction(t)

        b.sign(owner)

        chain.add_block(b)

    print("OWNER", chain.get_balance(owner.address))
    print("OTHER", chain.get_balance(other.address))

    a = time.time()
    chain.save_locally()

    print("TO SAVE", time.time() - a)
    a = time.time()

    newchain = Blockchain.from_local()

    print("TO RELOAD", time.time() - a)
