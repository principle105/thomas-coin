from base64 import b64decode, b64encode

import ecdsa
from base58 import b58decode, b58encode
from ecdsa import BadSignatureError, VerifyingKey
from tcoin.constants import CURVE, PREFIX


class Wallet:
    def __init__(self, secret: str = None):
        # Creating the signing key
        if secret is None:
            self.sk = ecdsa.SigningKey.generate(curve=CURVE)
        else:
            self.sk = ecdsa.SigningKey.from_string(
                bytes.fromhex(secret), curve=CURVE
            )

        # Verifying key
        self.vk: ecdsa.VerifyingKey = self.sk.get_verifying_key()

    @property
    def pk(self):
        """Private key"""
        return self.sk.to_string().hex()

    @property
    def address(self):
        return (
            PREFIX
            + b58encode(self.vk.to_string(encoding="compressed")).decode()
        )

    def sign(self, msg: str):
        return b64encode(self.sk.sign(msg.encode())).decode()

    @classmethod
    def is_signature_valid(
        cls, address: str, signature: str, msg: str
    ) -> bool:
        vk = cls.get_vk_from_address(address)

        try:
            vk.verify(b64decode(signature.encode()), msg.encode())
        except BadSignatureError:
            return False
        else:
            return True

    @classmethod
    def get_vk_from_address(cls, address: str):
        return VerifyingKey.from_string(
            b58decode(address[len(PREFIX) :]), curve=CURVE
        )
