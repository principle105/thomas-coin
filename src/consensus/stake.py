import ecdsa
from base58 import b58decode
from base64 import b64encode, b64decode
from wallet import Wallet
from hashlib import sha256
from constants import CURVE, STAKE_FEE


class Stake:
    def __init__(
        self, address: str, stake: int, hash: str = None, signature: str = None
    ):
        self.address = address
        self.stake = stake

        if hash is None:
            hash = self.get_hash()

        self.hash = hash
        self.signature = signature

    def get_hash(self):
        data = f"{self.address}{self.stake}"
        return sha256(data.encode()).hexdigest()

    def sign(self, wallet: Wallet):
        self.signature = b64encode(wallet.sk.sign(self.hash.encode())).decode()

    @property
    def staker_vk(self) -> ecdsa.VerifyingKey:
        return ecdsa.VerifyingKey.from_string(b58decode(self.address[1:]), curve=CURVE)

    def is_signature_verified(self) -> bool:
        """Checks if the block signature is valid"""
        try:
            return self.staker_vk.verify(
                b64decode(self.signature.encode()), self.hash.encode()
            )
        except ecdsa.BadSignatureError:
            return False

    def validate(self, chain_state):
        # Control decimal at 5 points
        self.stake = round(self.stake, 5)

        # Checking types
        if not all(
            isinstance(i, str) for i in [self.address, self.hash, self.signature]
        ):
            return False

        if not isinstance(self.stake, (float, int)):
            return False

        # Checking if signature matches
        if self.is_signature_verified() is False:
            return False

        # Checking if staking amount is above staking fee
        if STAKE_FEE >= self.stake:
            return False

        # Checking if wallet has enough to stake
        wallet = chain_state.wallets.get(self.address, None)

        if wallet is None or wallet.balance < self.stake:
            return False

        return True

    def get_json(self):
        data = {
            "address": self.address,
            "stake": self.stake,
            "hash": self.hash,
            "signature": self.signature,
        }
        return data

    @classmethod
    def from_json(cls, address, stake, hash, signature):
        return cls(address=address, stake=stake, hash=hash, signature=signature)
