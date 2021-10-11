GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1633628429.6876318,
    "transactions": [
        {
            "sender": "GENESIS",
            "sender_key": "GENESIS",
            "receiver": "Te32761fe9b7b617f327c5b428bd29d8b5b4d7929",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1633628429.687479,
            "hash": "88f318826e7a0ad341a5df53b9c0b922359b535fd8df22c6435aa28d1637dc04",
        }
    ],
    "hash": "216c5b5a7fb49f1420dcc615a12b9c7eddff04256612050474be699e8bf48aa3",
    "signature": "0",
}
MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters
MAX_COINS = 100000  # the maximum amount of coins issued (not including genesis)

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000
