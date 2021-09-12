import ecdsa
import time
from config import DEFAULT_FEE, LOWEST_FEE
from hashlib import sha256
from ecdsa.curves import SECP256k1
from blockchain.blockchain import Blockchain


class Transaction:
    def __init__(self, sender, receiver, amount, tip, timestamp=None, signature=None):
        """
        sender: sender public key
        receiver: receiver public address
        """

        if timestamp is None:
            self.timestamp = int(time.time())

        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature
        # Higher tip gives priority
        self.tip = tip

    def get_json(self):
        data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "signature": self.signature,
            "time": self.timestamp,
            "hash": self.hash(),
        }
        return data

    def get_raw_transaction_string(self):
        return f"{self.sender}{self.receiver}{self.amount}{self.timestamp}"

    def hash(self):
        data = self.get_raw_transaction_string().encode()
        return sha256(data).hexdigest()

    def sign(self, private_key: ecdsa.SigningKey):
        return private_key.sign(self.hash().encode())

    def is_signature_valid(self):
        sender_key = self.sender_public_key
        try:
            return sender_key.verify(
                signature=self.signature, data=self.hash().encode()
            )
        except ecdsa.BadSignatureError:
            return False

    @property
    def sender_public_key(self):
        key_string = bytes.fromhex(self.sender)
        return ecdsa.VerifyingKey.from_string(key_string, curve=SECP256k1)

    def validate(self, chain: Blockchain):
        # Checking if the sender key is valid
        try:
            _ = self.sender_public_key
        except ecdsa.MalformedPointError:
            raise Exception("Sender public key is invalid")

        fee = max((self.amount * DEFAULT_FEE), LOWEST_FEE)

        # Checking if the sender has enough coins to create the transaction


        # WORKING ON THIS


        

