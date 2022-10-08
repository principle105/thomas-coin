from typing import TYPE_CHECKING

from config import MAX_REQUEST_SIZE
from objsize import get_deep_size
from tcoin.tangle.messages import SignedPayload
from tcoin.utils import get_raw_hash

if TYPE_CHECKING:
    from ..nodes import Node, NodeConnection


class Request(SignedPayload):
    def __init__(
        self,
        *,
        node_id: str,
        payload: dict,
        timestamp: int = None,
        hash: str = None,
        signature: str = None,
        response: dict = None,
    ):

        super().__init__(
            node_id=node_id,
            payload=payload,
            timestamp=timestamp,
            hash=hash,
            signature=signature,
        )

        self.response = response

    def get_hash(self):
        raw_data = self.get_raw_data()

        return get_raw_hash(raw_data)

    def add_hash(self):
        self.hash = self.get_hash()

    def respond(self, client: "Node", node: "NodeConnection"):
        ...

    def receive(self, client: "Node", node: "NodeConnection"):
        ...

    def is_valid(self):
        # Checking if the request is too large
        data = self.to_dict()

        # Transaction does not exceed the maximum size
        if get_deep_size(data) > MAX_REQUEST_SIZE:
            return False

        # Checking if the hash matches the data
        if self.hash != self.get_hash():
            return False

        # Checking if the signature is valid
        if self.is_signature_valid is False:
            return False

        return True

    def to_dict(self) -> dict:
        return {**super().to_dict(), "response": self.response}
