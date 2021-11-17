from ecdsa.curves import SECP256k1

GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "GENESIS",
    "timestamp": 1635732093.6019998,
    "difficulty": 4,
    "reward": 0,
    "transactions": [
        {
            "sender": "GENESIS",
            "receiver": "T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
            "amount": 10000.0,
            "tip": 0.0,
            "nonce": 0,
            "data": "",
            "signature": "0",
            "timestamp": 1635732093.6016371,
            "hash": "d76ce9be52f5bfcf249387843d9f628bb2596fc4b7e35c857e1a6362ed124605",
        }
    ],
    "hash": "6510b53a5727f455a7c2a879401935e9d172ad8eb310c69c09323a0f11eab11a",
    "signature": "0",
}

# Elliptic curve used to generate addresses
CURVE = SECP256k1

MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters

# Maximum amount of coins issued (not including genesis)
MAX_COINS = 100000

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000

# Initial lottery number
INITIAL_NUMBER = 1

# Minimum amount of coins that can be staked
# Staking fee is subtracted from staking amount
STAKE_FEE = 2

# Maximum amount of stake that will affect the lottery
# (prevent a few individuals from holding the most power)
MAX_AFFECTING_STAKE = 32

# Amount of time between each block
# TODO: Calculate the block time based on current efficiency of network
BLOCK_INTERVAL = 20  # seconds
