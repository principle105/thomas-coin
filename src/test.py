from transaction import Transaction
from wallet import Wallet
from blockchain import Blockchain, Block
import time

chain = Blockchain()

user1 = Wallet("e9178717073571d0c82cab7d8c21f23e32ce7e2cbe6d0faf12a855fbd19da079")
user2 = Wallet("0fcfe4770860e457c7f5f38a9cd94ccfe2ff8711bb931509529ae70bd523d2ba")

t = Transaction(
    sender="GENESIS",
    receiver=user1.address,
    amount=1000,
    tip=10,
)
t.signature = "GENESIS"

t2 = Transaction(
    sender=user1.public_key,
    receiver=user2.address,
    amount=100,
    tip=10,
)
t2.sign(user1.sk)

block1 = Block("0", "0", "0", str(time.time()), [t, t2])

# block1.sign(user.sk)
block1.signature = "0"

print(block1.get_json())

chain.chain.append(block1)

a = chain.get_balance("T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6")

print(a)