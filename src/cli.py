import typer
import getpass
import requests
from typer.colors import BRIGHT_YELLOW, BRIGHT_BLUE
from wallet import Wallet
from node import Node
from blockchain import Blockchain

app = typer.Typer()


def get_public_ip():
    return requests.get("https://api.ipify.org").text


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

    # Creating blockchain
    chain = Blockchain.from_local()

    pk = getpass.getpass(prompt="Your Private Key: ")

    wallet = Wallet(pk)

    # Initializing node
    node = Node(host=host, port=port, chain=chain, max_connections=30)

    # Starting node
    print("Starting node")
    node.start()

    # Trying to connect to unl nodes
    node.connect_to_unl_nodes()

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


if __name__ == "__main__":
    app()
