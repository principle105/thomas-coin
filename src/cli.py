import typer
import getpass
from typer.colors import BRIGHT_YELLOW, BRIGHT_BLUE
from wallet import Wallet
from node import Node
from blockchain import Blockchain, Block, Transaction

app = typer.Typer()


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

    # Initializing node
    node = Node(host, port)

    # Starting node
    node.start()

    pk = getpass.getpass(prompt="Your Private Key: ")
    wallet = Wallet(pk)

    # For testing
    while True:
        chain = Blockchain.from_local()

        chain.set_main(chain, False)

        a = input("What do: ") or "connect"
        if a == "connect":
            node.connect_to_unl_nodes()

        elif a == "send":
            adr = input("Receiver Address: ")

            amt = float(input("Amount: "))

            t = chain.create_trans(wallet, adr, amt, 0)

            if chain.add_pending(t):
                node.send_transaction(t.get_json())

        elif a == "connect-single":
            host = input("Host: ") or "127.0.0.1"
            port = int(input("Port: ") or 3000)
            node.connect_to_node(host, port)
        elif a == "ask":
            node.request_chain()

        elif a == "pending":
            print(chain.pending)

        elif a == "bal":
            wallet = chain.state.get_wallet(input("Address: "))
            print(chain.state.wallets)
            print(f"Balance: {wallet.balance} Nonce: {wallet.nonce}")


if __name__ == "__main__":
    app()
