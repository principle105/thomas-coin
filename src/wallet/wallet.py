import ecdsa
from ecdsa.curves import SECP256k1
from base58 import b58encode


class Wallet:
    def __init__(self, secret: str = None):
        # Creating the signing key
        if secret is None:
            self.sk = ecdsa.SigningKey.generate(curve=SECP256k1)
        else:
            self.sk = ecdsa.SigningKey.from_string(
                bytes.fromhex(secret), curve=ecdsa.SECP256k1
            )

        # Verifying key
        self.vk = self.sk.get_verifying_key()

        self.private_key = self.sk.to_string().hex()

        self.address = (
            "T" + b58encode(self.vk.to_string(encoding="compressed")).decode()
        )
