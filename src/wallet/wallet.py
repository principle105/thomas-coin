import ecdsa
from ecdsa.curves import SECP256k1
from hashlib import sha256


class Wallet:
    def __init__(self, secret: str = None):
        # Creating the signing key
        if secret is None:
            print("Generating a new wallet")
            self.sk = ecdsa.SigningKey.generate(curve=SECP256k1)
        else:
            self.sk = ecdsa.SigningKey.from_string(
                bytes.fromhex(secret), curve=ecdsa.SECP256k1
            )

        # Verifying key
        self.vk = self.sk.get_verifying_key()

        self.public_key = self.vk.to_string().hex()

        self.private_key = self.sk.to_string().hex()

        self.address = Wallet.convert_to_address(self.public_key)

    # https://ethereum.stackexchange.com/questions/3542/how-are-ethereum-addresses-generated
    @classmethod
    def convert_to_address(cls, public_key: str):
        return (
            "T"
            + sha256(
                sha256(public_key.encode("utf-8")).hexdigest().encode("utf-8")
            ).hexdigest()[-40:]
        )
