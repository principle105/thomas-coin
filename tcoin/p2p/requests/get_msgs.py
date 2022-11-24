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

    def receive(self, client: "Node", node: "NodeConnection"):
        msgs = self.response

        # Checking if there were messages returned in the response
        if msgs is None:
            return

        initial = self.payload["initial"]
        requested_msgs = self.payload["msgs"]

        # Serializing the initial message
        if (initial := client.serialize_msg(initial)) is False:
            return

        pending = client.scheduler.p_pending.get(initial.hash, None)

        # Checking if the initial message is still pending
        if pending is None:
            return

        for _id, m in msgs.items():
            # Checking if the message is still pending
            if _id not in pending.missing:
                continue

            # Checking if the message was requested
            if _id not in requested_msgs:
                continue

            if m is not None:
                # Checking if the returned message is serializable
                if (m := client.serialize_msg(m)) is False:
                    continue

            # Casting for the message
            pending.add_vote(node.id, _id, m)

        client.scheduler.update_pending(pending)
