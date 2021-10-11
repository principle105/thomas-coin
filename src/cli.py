import typer
import getpass
import requests
import logging
from typer.colors import BRIGHT_YELLOW, BRIGHT_BLUE
from config import LOG_PATH
from wallet import Wallet
from node import Node
from blockchain import Blockchain

app = typer.Typer()


def get_public_ip():
    return requests.get("https://api.ipify.org").text


def create_logger(host, port):
    logging.basicConfig(
        filename=f"{LOG_PATH}{host}:{port}.log",
        level=logging.DEBUG,
        style="{",
        format="{asctime}:{name} {message}",
        filemode="w",
    )


@app.command()
def wallet():

    secret = input("Wallet secret: ")
    if not secret:
        secret = None

    wallet = Wallet(secret=secret)
    typer.secho(f"ADDRESS: {wallet.address}", fg=BRIGHT_BLUE)
    typer.secho(f"PRIVATE KEY: {wallet.private_key}", fg=BRIGHT_YELLOW)


@app.command()
def node():

    host = input("Host: ") or "127.0.0.1"
    port = int(input("Port: ") or 3000)
    full_node = not bool(input("Full Node: "))

    print("Full Node", full_node)

    # Creating blockchain
    chain = Blockchain.from_local()

    pk = getpass.getpass(prompt="Your Private Key: ")

    wallet = Wallet(pk)

    # Initializing node
    node = Node(
        host=host, port=port, chain=chain, max_connections=30, full_node=full_node
    )

    # Starting node
    print("Starting node")
    node.start()

    # Creating logger
    create_logger(host, port)

    # Trying to connect to unl nodes
    if node.connect_to_unl_nodes() is False:
        print("Unable to connect to any unl nodes")

    # Asking for blockchain from unl nodes
    node.request_chain()

    # Asking for pending transactions
    node.send_data_to_nodes("sendpending", {})

    # For testing
    while True:

        a = input("What do: ") or "connect"

        if a == "connect":
            node.connect_to_unl_nodes()

        elif a == "connect-single":
            host = input("Host: ") or "127.0.0.1"
            port = int(input("Port: ") or 3000)
            node.connect_to_node(host, port)

        elif a == "send":
            adr = input("Receiver Address: ")

            amt = float(input("Amount: "))

            t = chain.create_trans(wallet, adr, amt, 0)

            if chain.add_pending(t):
                node.send_transaction(t.get_json())

        elif a == "pending":
            print(chain.pending)

        elif a == "bal":
            address = input("Address: ") or wallet.address

            balance = chain.get_balance(address)

            print(f"Balance: {balance}")

        elif a == "conn":
            print(len(node.nodes_outbound) + len(node.nodes_inbound))


if __name__ == "__main__":
    app()
