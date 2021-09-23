import json
from config import CONNECTED_NODE_PATH, INITIAL_NODE_PATH


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

    with open(CONNECTED_NODE_PATH, "w") as f:
        json.dump(node_list, f)


def get_unl_nodes():
    with open(INITIAL_NODE_PATH, "rb") as f:
        return json.load(f)


def node_is_unl(node_id):
    for unl in get_unl_nodes():
        if node_id == unl:
            return True
    return False
