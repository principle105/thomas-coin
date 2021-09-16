from transaction import Transaction
from wallet import Wallet
from blockchain import Blockchain, Block

chain = Blockchain()

sender = Wallet("e9178717073571d0c82cab7d8c21f23e32ce7e2cbe6d0faf12a855fbd19da079")

t = Transaction(
    sender="971a12a0d1c9068167226ff46eca48b2db547206e2adef193db7596cb30578a1fef2907db56dfb534efafd98776b77f13f74beee7c2b1f4d943f20cda6d31aff",
    receiver="T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6",
    amount=1000,
    tip=10,
)

t.sign(sender.sk)

block1 = Block(
    "0", "0", "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6 ", "1631749808.558269", [t]
)

block1.sign(sender.sk)

print(block1.get_json())


# sender = Wallet()
# receiver = Wallet()

# t = Transaction(sender.public_key, receiver.address, 100, 0)
# signature = t.sign(sender.private_key)
# t.signature = signature

# print(t.is_signature_valid())


{
    "index": "0",
    "prev": "0",
    "forger": "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6 ",
    "timestamp": "1631749808.558269",
    "transactions": (
        [
            {
                "sender": "971a12a0d1c9068167226ff46eca48b2db547206e2adef193db7596cb30578a1fef2907db56dfb534efafd98776b77f13f74beee7c2b1f4d943f20cda6d31aff",
                "receiver": "T977e7b212b29a2b0fcc30d2c2db83c71ad1161c6",
                "amount": 1000,
                "signature": None,
                "time": "1631750981.983847",
                "hash": "0f9f47c409085576158ceb648e27a72a7aec93711364cd84e442f6d8062bacc6",
            }
        ],
    ),
    "hash": "14647ca103d4a9a415a863f937a509d8223f8286bb0848359a5712dea616236b",
    "signature": None,
}
