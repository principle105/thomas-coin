import json
from config import CONNECTED_NODE_PATH


def get_connected_nodes():
    with open(CONNECTED_NODE_PATH, "rb") as f:
        return json.load(f)


def save_connected_node(host, port, id):
    node_list = get_connected_nodes()

    in_list = False

    for node in node_list:
        if node_list[node]["host"] == host and node_list[node]["port"] == port:
            in_list = True

    if not in_list:
        node_list[id] = {"host": host, "port": port}
