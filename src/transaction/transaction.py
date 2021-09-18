import ecdsa
import time
from config import DEFAULT_FEE, LOWEST_FEE
from hashlib import sha256
from ecdsa.curves import SECP256k1
from base64 import b64encode, b64decode


class Transaction:
    def __init__(
        self,
        sender_key: str,
        receiver: str,
        amount: int,
        tip: int,
        timestamp: float = None,
        signature: str = None,
        hash: str = None,
        sender: str = None,
    ):
        """
        sender_key: sender public key
        receiver: receiver public address
        amount: coins being sent
        tip: transaction tip
        timestamp: timestamp of transaction (seconds since the epoch)
        signature: proves that sender approved the transaction
        """

        if timestamp is None:
            timestamp = time.time()

        self.timestamp = timestamp

        if sender is None:
            sender = self.convert_to_address(sender_key)

        self.sender = sender

        self.sender_key = sender_key

        self.receiver = receiver

        self.amount = amount

        # Higher tip gives priority
        self.tip = tip

        self.signature = signature

        if hash is None:
            hash = self.get_hash()

        self.hash = hash

    # https://ethereum.stackexchange.com/questions/3542/how-are-ethereum-addresses-generated
    def convert_to_address(self, public_key: str):
        return (
            "T"
            + sha256(
                sha256(public_key.encode("utf-8")).hexdigest().encode("utf-8")
            ).hexdigest()[-40:]
        )

    @property
    def sender_public_key(self):
        key_string = bytes.fromhex(self.sender_key)
        return ecdsa.VerifyingKey.from_string(key_string, curve=SECP256k1)

    def get_json(self):
        data = {
            "sender": self.sender,
            "sender_key": self.sender_key,
            "receiver": self.receiver,
            "amount": self.amount,
            "tip": 0,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }
        return data

    def get_raw_transaction_string(self):
        return f"{self.sender}{self.receiver}{self.amount}{self.timestamp}"

    def get_hash(self) -> str:
        data = self.get_raw_transaction_string().encode()
        return sha256(data).hexdigest()

    def sign(self, private_key: ecdsa.SigningKey):
        self.signature = b64encode(private_key.sign(self.hash.encode())).decode()

    def is_signature_valid(self):
        sender_key = self.sender_public_key
        try:
            return sender_key.verify(
                signature=b64decode(self.signature.encode()), data=self.hash.encode()
            )
        except ecdsa.BadSignatureError:
            return False

    def validate(self, chain):
        # Checking if the sender key is valid
        try:
            _ = self.sender_public_key
        except ecdsa.MalformedPointError:
            raise Exception("Sender public key is invalid")

        fee = max((self.amount * DEFAULT_FEE), LOWEST_FEE)

        # Checking if the sender has enough coins to create the transaction

        # WORKING ON THIS

    @classmethod
    def from_json(
        cls, sender, sender_key, receiver, amount, tip, timestamp, signature, hash
    ):
        return cls(
            sender=sender,
            sender_key=sender_key,
            receiver=receiver,
            amount=int(amount),
            tip=int(tip),
            timestamp=timestamp,
            signature=signature,
            hash=hash,
        )
