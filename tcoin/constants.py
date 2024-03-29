from ecdsa.curves import SECP256k1

# Wallets
CURVE = SECP256k1
PREFIX = "T"

# Currency details
MIN_SEND_AMT = 1  # minimum amount of coins that can be sent in a transaction

# Messages
MAX_TIP_AGE = 60 * 60 * 24  # maximum age before an unverified tip is purged
MAX_PARENTS = 8  # maximum amount of parents a message can have
MIN_STRONG_PARENTS = 1  # minimum amount of strong parents a message must have
MAX_MSG_SIZE = 4096  # maximum size of a message in bytes
MAX_PARENT_AGE = (
    60 * 60
)  # maximum age a parent can be older than a child message

# Branches
MAIN_THRESHOLD = 0.5  # percent higher that a branch must be than the next highest branch to be considered the main branch
FINALITY_SCORE = 4  # approval weight of a branch for it to be considered final

# Scheduler
DEFAULT_SCHEDULING_RATE = 0.05  # how often the scheduler should run in seconds
UPDATE_RATE = (
    15  # message interval that the scheduler should update the scheduling rate
)
PENDING_THRESHOLD = (
    3  # reputation threshold for a pending message to be considered valid
)
PENDING_WINDOW = 4  # seconds

# Request
MAX_REQUEST_SIZE = 16384  # maximum size of a request in bytes

# Pow
MAX_NONCE = 2**32
BASE_DIFFICULTY = 10
GAMMA = 0.2
TIME_WINDOW = 60  # seconds

# Genesis Message
GENESIS_MSG_DATA = {
    "node_id": "0",
    "value": "transaction",
    "payload": {
        "receiver": "TmANJZAiiZTjBiLZt2QDKoYVtLn8yHGPdXdydymbPVJDZ",
        "amt": 25000,
    },
    "index": 0,
    "parents": {},
    "timestamp": 1653266909,
    "nonce": 0,
    "hash": "0",
    "signature": "0",
}
