GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1634442655.099822,
    "difficulty": 0,
    "transactions": [
        {
            "sender": "GENESIS",
            "sender_key": "GENESIS",
            "receiver": "Te32761fe9b7b617f327c5b428bd29d8b5b4d7929",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1634442655.099783,
            "hash": "e3b6f7da2343eccf0ae509ce3482b48a29600550215f40cef04a4938f77a6a43",
        }
    ],
    "hash": "6f54b3618ef651646570288329d2f0759bf1c35a8af9a5a6dd5714c7e3d661f1",
    "signature": "0",
}
MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters

# Maximum amount of coins issued (not including genesis)
MAX_COINS = 100000

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000

# Amount of initial blocks that do not require to be minted with coins
NO_COIN_AMOUNT = 100
