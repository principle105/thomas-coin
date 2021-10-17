GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1634506769.152265,
    "difficulty": 0,
    "transactions": [
        {
            "sender": "GENESIS",
            "receiver": "T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1634506769.152102,
            "hash": "69f94b78dcd1e5654edfed78c7eca1233eb9973f624cf06c63ab4d72ecf06add",
        }
    ],
    "hash": "2948a462bb6878119eff1c9e03aed07694d31a6aef819205b0d2dba90bead985",
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
