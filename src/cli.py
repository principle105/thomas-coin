import typer
from typer.colors import BRIGHT_YELLOW, BRIGHT_BLUE
from wallet import Wallet
from node import Node
from blockchain import Blockchain, Block

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
    fraud = bool(input("FRAUD: "))
    if fraud:
        chain = Blockchain()
        for i in range(3):
            chain.blocks.append(Block(i, "0"))
    else:
        chain = Blockchain.from_local()

    # Initializing node
    node = Node(host, port)

    # Starting node
    node.start()

    while True:
        chain = Blockchain.from_local()

        chain.set_main(chain, False)

        a = input("What do: ") or "connect"
        if a == "connect":
            host = input("Host: ") or "127.0.0.1"
            port = int(input("Port: ") or 3000)
            node.connect_to_node(host, port)
        elif a == "ask":
            node.request_chain()


if __name__ == "__main__":
    app()
