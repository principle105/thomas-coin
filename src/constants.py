from ecdsa.curves import SECP256k1

GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "GENESIS",
    "timestamp": 1635138318.75742,
    "difficulty": 4,
    "reward": 0,
    "transactions": [
        {
            "sender": "GENESIS",
            "receiver": "T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1635138318.757374,
            "hash": "85df2718e0344dcae1a66e21debefb14be3309212d42f9b3f5ad9b9c33843eb5",
        }
    ],
    "hash": "4638821efddac5c388d27e3cda292fb0001bb0b436158c53e3cfade68f4e31ec",
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

# Amount of initial blocks that do not require to be minted with coins
NO_COIN_AMOUNT = 100

# Initial lottery number
INITIAL_NUMBER = 1

# Minimum amount of coins that can be staked
# Staking fee is subtracted from staking amount
STAKE_FEE = 2

# Maximum amount of stake that will affect the lottery
# (prevent a few individuals from holding the most power)
MAX_AFFECTING_STAKE = 32
