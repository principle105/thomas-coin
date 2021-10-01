GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1632890813.8105001,
    "transactions": [
        {
            "sender": "GENESIS",
            "sender_key": "GENESIS",
            "receiver": "Te32761fe9b7b617f327c5b428bd29d8b5b4d7929",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1632890813.8103418,
            "hash": "e40d94799d76ff5e36654f786a0d05a4e1c65ca9b4c1138a7dfafa6eba1760d9",
        }
    ],
    "hash": "67751311e9dfc219d2452b2969e6666a6cd8acfb2d1d2cb5b3fa0f5b1053f87a",
    "signature": "0",
}
MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters
MAX_COINS = 100000  # the maximum amount of coins issued (not including genesis)

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000
