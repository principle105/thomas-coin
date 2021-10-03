GENESIS_BLOCK_DATA = {
    "index": 0,
    "prev": "0",
    "forger": "0",
    "timestamp": 1633270314.217898,
    "transactions": [
        {
            "sender": "GENESIS",
            "sender_key": "GENESIS",
            "receiver": "T6a0459220225c6b4bfaef26ec87844a072afc29a",
            "amount": 10000.0,
            "tip": 0,
            "nonce": 0,
            "signature": "0",
            "timestamp": 1633270314.217428,
            "hash": "77034b046efebbf915d3da176ad234581a4e774876bd0f685e05e401e822ecd9",
        }
    ],
    "hash": "c22bdff26215d7485d1bcac4206a9f9eb8a1aa5a6aae73097e70b91d8b7b7829",
    "signature": "0",
}
MAX_BLOCK_SIZE = 50  # transactions
MAX_TRANSACTION_SIZE = 700  # characters
MAX_COINS = 100000  # the maximum amount of coins issued (not including genesis)

# Interval of blocks until coins issued per block is changed
ISSUE_CHANGE_INTERVAL = 10000
