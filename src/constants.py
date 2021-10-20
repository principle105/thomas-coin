from ecdsa.curves import SECP256k1

GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1634510723.853075,
    "difficulty": 4,
    "transactions": [
        {
            "sender": "GENESIS",
            "receiver": "T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1634510723.85303,
            "hash": "2ac9b90767b21098b4fd005b4a37056445f24e826fda8f1aa467a2fa0a6b99da",
        }
    ],
    "hash": "84ca05ed450e3dfc77c2da4680c9bbeb39ee36389c00de8cb64fd6539c4b2d27",
    "signature": "0",
}
CURVE = SECP256k1

MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters

# Maximum amount of coins issued (not including genesis)
MAX_COINS = 100000

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000

# Amount of initial blocks that do not require to be minted with coins
NO_COIN_AMOUNT = 100
