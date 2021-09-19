from blockchain import Blockchain, Block
from wallet import Wallet
from transaction import Transaction
from os import getenv

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

def send(blockchain: Blockchain, wallet: Wallet, receiver: str, amount: int) -> Block:
    chain = blockchain.chain

    block = Block(len(chain), chain[-1].hash)

    t = Transaction(wallet.public_key, receiver, amount, 10)

    t.sign(wallet)

    block.append_transaction(t)

    block.sign(wallet)

    return block

if __name__ == "__main__":
    owner = Wallet(getenv("OWNER_PRIVATE_KEY"))

    other = Wallet("1ef98e260c70ae196079655392461226c42778b8373ba9780e497272e47d53dc")

    chain = Blockchain()

    block = send(chain, owner, other.address, 100)

    chain.add_block(block)

    print("OWNER",chain.get_balance(owner.address))
    print("OTHER",chain.get_balance(other.address))