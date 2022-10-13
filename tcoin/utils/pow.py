from hashlib import sha256

from tcoin.constants import MAX_NONCE


def get_target(difficulty: int) -> int:
    return 2 ** (256 - difficulty)


def is_valid_hash(hash_str: str, target: int) -> bool:
    return int(hash_str, 16) < target


def get_raw_hash(msg: str) -> str:
    return sha256(msg.encode()).hexdigest()


def get_pow_hash(msg: str, nonce: int) -> str:
    return get_raw_hash(f"{msg}{nonce}")


def pow(msg: str, difficulty: int):
    target = get_target(difficulty)

    for nonce in range(MAX_NONCE):
        hash_result = get_pow_hash(msg, nonce)

        if is_valid_hash(hash_result, target):
            return hash_result, nonce

    return False
