from typing import TYPE_CHECKING

from tcoin.utils import check_var_types

if TYPE_CHECKING:
    from ..nodes import Node, NodeConnection

from .request import Request


class DiscoverPeers(Request):
    value = "discover-peers"

    def respond(self, client, node):
        nodes = {n.id: [n.host, n.port] for n in client.nodes_outbound}

        nodes.update(client.other_nodes)

        if node.id in nodes:
            del nodes[node.id]

        return nodes

    def receive(self, client: "Node", node: "NodeConnection"):
        for _id, (host, port) in self.response.items():

            if all(check_var_types((host, str), (port, int))):
                client.other_nodes[_id] = [host, port]
