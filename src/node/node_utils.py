import json
from config import UNL_PATH

def get_unl():
    with open(UNL_PATH, "r") as f:
        return json.load(f)

def node_is_unl(host, port):
    return {"host": host, "port": port} in get_unl()
