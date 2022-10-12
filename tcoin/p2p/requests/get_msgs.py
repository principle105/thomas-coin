import random
from typing import TYPE_CHECKING

from tcoin.config import max_tips_requested
from tcoin.utils import check_var_types

if TYPE_CHECKING:
    from ..nodes import Node, NodeConnection

from .request import Request


# TODO: send in chunks
class GetMsgs(Request):
    value = "get-msgs"

    def respond(self, client: "Node", node: "NodeConnection"):
        # TODO: do some payload validation, make sure history is only True when needed

        # The tips that are requests
        tips = self.payload.get("msgs", None)

        # Whether or
        history = self.payload.get("history", None)

        if tips is None or history is None:
            return None

        if any(check_var_types((tips, list), (history, bool))) is False:
            return None

        if len(tips) > max_tips_requested:
            tips = random.sample(tips, max_tips_requested)

        if history:
            children = {}

            for t in tips:
                children = client.tangle.get_direct_children(t)

                if children is None:
                    continue

                for _id, msg in children.values():
                    if _id in children:
                        continue
                    children[_id] = msg.to_dict()

        else:
            children = {}

            for t in tips:
                msg = client.tangle.get_msg(t)

                children[t] = None if msg is None else msg.to_dict()

        return children

    def receive(self, client: "Node", _):
        msgs = self.response

        if msgs is None:
            return

        for _id, m in msgs.items():
            # Checking if the message was requested
            if _id not in self.payload.get("msgs", []):
                continue

            if m is None:
                continue

            if (msg := client.serialize_msg(m)) is False:
                continue

            client.add_new_msg(msg)
