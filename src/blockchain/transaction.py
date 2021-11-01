import ecdsa
import time
from hashlib import sha256
from base64 import b64encode, b64decode
from base58 import b58decode
from wallet import Wallet
from constants import MAX_TRANSACTION_SIZE, CURVE
from typing import TYPE_CHECKING

# To avoid circular imports
if TYPE_CHECKING:
    from .state import State


class Transaction:
    def __init__(
        self,
        sender: str,
        receiver: str,
        amount: float,
        tip: float,
        nonce: int,
        timestamp: float = None,
        data: str = "",
        signature: str = None,
        hash: str = None,
    ):
        """
        sender: sender address
        receiver: receiver address
        amount: coins being sent
        tip: transaction tip
        nonce: account nonce
        timestamp: timestamp of transaction (seconds since the epoch)
        data: data that the sender wants to include
        signature: proves that sender approved the transaction
        hash: transaction hash
        """

        if timestamp is None:
            timestamp = time.time()
        self.timestamp = timestamp

        self.sender = sender

        self.receiver = receiver

        self.amount = amount

        # Higher tip gives priority
        self.tip = tip

        self.nonce = nonce

        self.data = data

        self.signature = signature

        if hash is None:
            hash = self.get_hash()

        self.hash = hash

    @property
    def sender_vk(self) -> ecdsa.VerifyingKey:
        return ecdsa.VerifyingKey.from_string(b58decode(self.sender[1:]), curve=CURVE)

    def get_json(self):
        data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tip": self.tip,
            "nonce": self.nonce,
            "data": self.data,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }
        return data

    def get_raw_transaction_string(self):
        return f"{self.sender}{self.receiver}{self.tip}{self.amount}{self.timestamp}{self.nonce}{self.data}"

    def get_hash(self) -> str:
        data = self.get_raw_transaction_string().encode()
        return sha256(data).hexdigest()

    def sign(self, wallet: Wallet):
        self.signature = b64encode(wallet.sk.sign(self.hash.encode())).decode()

    def is_signature_valid(self):
        try:
            return self.sender_vk.verify(
                signature=b64decode(self.signature.encode()), data=self.hash.encode()
            )
        except ecdsa.BadSignatureError:
            return False

    def validate(self, chain_state: "State"):
        # Control decimal at 5 points
        self.amount = round(self.amount, 5)
        self.tip = round(self.tip, 5)

        # Checking if transactions are the correct type
        if not all(
            isinstance(i, (float, int)) for i in [self.amount, self.tip, self.timestamp]
        ):  
            return False

        if not all(
            isinstance(i, str)
            for i in [self.sender, self.receiver, self.signature, self.hash, self.data]
        ):
            return False

        
        if not isinstance(self.nonce, int):
            return False

        # Checking if transaction exceeds character limit
        if len(str(self.get_json())) > MAX_TRANSACTION_SIZE:
            return False

        # Checking if amount is valid
        if self.amount < 0:
            return False

        # Checking if amount is valid
        if self.tip < 0:
            return False

        # Checking if the signature is valid and matches transaction data
        if self.is_signature_valid() is False:
            return False

        # Using get instead of get_wallet method to prevent from creating new wallet in storage
        wallet = chain_state.wallets.get(self.sender, None)

        # Checking if the sender has enough coins to create the transaction
        if wallet is None or wallet.balance < self.amount + self.tip:
            return False

        # Checking if nonce is invalid
        if wallet.nonce >= self.nonce:
            return False

        return True

    @classmethod
    def from_json(
        cls,
        sender,
        receiver,
        amount,
        tip,
        nonce,
        timestamp,
        data,
        signature,
        hash,
    ):
        return cls(
            sender=sender,
            receiver=receiver,
            amount=float(amount),
            tip=float(tip),
            nonce=nonce,
            timestamp=timestamp,
            data=data,
            signature=signature,
            hash=hash,
        )
